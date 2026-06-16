"""Fetch trending / recent papers from Semantic Scholar API.

Semantic Scholar provides a free, open API covering papers across all venues
(not limited to arXiv).  This serves as an alternative academic source similar
to Web of Science but without institutional access requirements.

Docs: https://api.semanticscholar.org/
"""

from __future__ import annotations

import random
import time
from datetime import datetime
from typing import Any

import requests

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "title,abstract,url,year,citationCount,referenceCount,publicationVenue,authors,externalIds,publicationDate"
# Sort options for bulk search: publicationDate:asc (从早到晚) or publicationDate:desc (从晚到早)
DEFAULT_SORT = "publicationDate:desc"
DEFAULT_TIMEOUT = 30
DEFAULT_HEADERS = {
    "User-Agent": "iDeer-daily-recommender/1.0",
}


def _get_default_year() -> str:
    """Return default year filter: current year onwards (e.g. '2025-')."""
    return f"{datetime.now().year}-"


def search_recent_papers(
    query: str,
    max_results: int = 60,
    year: str | None = None,
    fields_of_study: list[str] | None = None,
    sort: str = DEFAULT_SORT,
    timeout: int = DEFAULT_TIMEOUT,
    api_key: str = "",
) -> list[dict[str, Any]]:
    """Search for recent papers matching *query*.

    Parameters
    ----------
    query : str
        Free-text search query (e.g. research interests).
    max_results : int
        Maximum number of papers to return.
    year : str | None
        Year filter, e.g. "2024-" for papers from 2024 onward.
        Defaults to current year onwards (e.g. "2025-") if not specified.
    fields_of_study : list[str] | None
        Optional Semantic Scholar field of study filters
        (e.g. ["Computer Science", "Medicine"]).
    sort : str
        Sort order for results. Default is "publicationDate:desc" (从晚到早).
        Options: "publicationDate:asc" or "publicationDate:desc".
    api_key : str
        Optional Semantic Scholar API key for higher rate limits.
    """
    headers = dict(DEFAULT_HEADERS)
    if api_key:
        headers["x-api-key"] = api_key

    # Apply default year filter to ensure only recent papers are returned
    if not year:
        year = _get_default_year()

    papers: list[dict[str, Any]] = []
    offset = 0
    batch = min(100, max_results)

    while len(papers) < max_results:
        params: dict[str, Any] = {
            "query": query,
            "limit": batch,
            "offset": offset,
            "fields": FIELDS,
            "sort": sort,
            "year": year,
        }
        if fields_of_study:
            params["fieldsOfStudy"] = ",".join(fields_of_study)

        # Use bulk endpoint which supports sort parameter
        resp = requests.get(
            f"{BASE_URL}/paper/search/bulk",
            params=params,
            headers=headers,
            timeout=timeout,
        )
        if resp.status_code == 429:
            print("[semanticscholar] Rate limited, sleeping 5s...")
            time.sleep(5)
            continue
        resp.raise_for_status()

        data = resp.json()
        batch_papers = data.get("data", [])
        if not batch_papers:
            break

        for p in batch_papers:
            papers.append(_normalize_paper(p))
            if len(papers) >= max_results:
                break

        total = data.get("total", 0)
        offset += len(batch_papers)
        if offset >= total:
            break

        time.sleep(random.uniform(0.5, 1.5))

    return papers


def fetch_papers_for_queries(
    queries: list[str],
    max_results_per_query: int = 40,
    year: str | None = None,
    fields_of_study: list[str] | None = None,
    sort: str = DEFAULT_SORT,
    api_key: str = "",
    sleep_range: tuple[float, float] = (1.0, 3.0),
) -> list[dict[str, Any]]:
    """Fetch papers for multiple query strings, dedup by paperId."""
    seen: dict[str, dict] = {}
    for query in queries:
        results = search_recent_papers(
            query,
            max_results=max_results_per_query,
            year=year,
            fields_of_study=fields_of_study,
            sort=sort,
            api_key=api_key,
        )
        for paper in results:
            pid = paper.get("paper_id", "")
            if pid and pid not in seen:
                seen[pid] = paper
        print(f"[semanticscholar] {len(results)} papers fetched for query: {query!r}")
        if len(queries) > 1:
            time.sleep(random.uniform(*sleep_range))
    return list(seen.values())


def _normalize_paper(raw: dict[str, Any]) -> dict[str, Any]:
    """Convert Semantic Scholar API response to a flat dict."""
    authors = raw.get("authors") or []
    author_names = ", ".join(a.get("name", "") for a in authors[:5])
    if len(authors) > 5:
        author_names += " et al."

    venue = raw.get("publicationVenue") or {}
    venue_name = venue.get("name", "") if isinstance(venue, dict) else ""

    external = raw.get("externalIds") or {}
    arxiv_id = external.get("ArXiv", "")
    doi = external.get("DOI", "")

    url = raw.get("url", "")
    if not url and arxiv_id:
        url = f"https://arxiv.org/abs/{arxiv_id}"
    if not url and doi:
        url = f"https://doi.org/{doi}"

    return {
        "paper_id": raw.get("paperId", ""),
        "title": raw.get("title", "Untitled"),
        "abstract": raw.get("abstract") or "",
        "url": url,
        "year": raw.get("year") or "",
        "citation_count": raw.get("citationCount") or 0,
        "reference_count": raw.get("referenceCount") or 0,
        "authors": author_names,
        "venue": venue_name,
        "arxiv_id": arxiv_id,
        "doi": doi,
        "publication_date": raw.get("publicationDate") or "",
    }
