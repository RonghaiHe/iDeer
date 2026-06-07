from __future__ import annotations

import math
import re
from collections import Counter
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen



_PAPER_TYPES = {"conferencePaper", "journalArticle", "preprint"}
_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [tok.lower() for tok in _TOKEN_RE.findall(text)]


def _read_text(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    return p.read_text(encoding="utf-8").strip()


def _match_any(path: str, patterns: list[str]) -> bool:
    posix = PurePosixPath(path)
    for pattern in patterns:
        if fnmatchcase(path, pattern) or posix.match(pattern):
            return True
    return False


def _extract_text(item: dict[str, Any]) -> str:
    parts = [
        str(item.get("title", "") or ""),
        str(item.get("abstract", "") or ""),
        str(item.get("summary", "") or ""),
    ]
    return "\n".join(parts)


class ZoteroCorpusClient:
    def __init__(
        self,
        user_id: str,
        api_key: str,
        include_path: list[str] | None = None,
        ignore_path: list[str] | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self.user_id = user_id
        self.api_key = api_key
        self.include_path = include_path or []
        self.ignore_path = ignore_path or []
        self.timeout_seconds = timeout_seconds
        self.base = f"https://api.zotero.org/users/{user_id}"
        self.headers = {"Zotero-API-Key": api_key}

    def _get(self, path: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        query = urlencode(params or {}, doseq=True)
        url = f"{self.base}/{path}"
        if query:
            url = f"{url}?{query}"
        req = Request(url=url, headers=self.headers, method="GET")
        with urlopen(req, timeout=self.timeout_seconds) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
        import json
        payload = json.loads(body)
        if not isinstance(payload, list):
            return []
        return payload

    def _fetch_collections(self) -> dict[str, dict[str, Any]]:
        start = 0
        page_size = 100
        collections: dict[str, dict[str, Any]] = {}
        while True:
            batch = self._get("collections", {"format": "json", "limit": page_size, "start": start})
            if not batch:
                break
            for col in batch:
                key = str(col.get("key", ""))
                if key:
                    collections[key] = col
            if len(batch) < page_size:
                break
            start += len(batch)
        return collections

    def _collection_path(self, key: str, collections: dict[str, dict[str, Any]], cache: dict[str, str]) -> str:
        if key in cache:
            return cache[key]
        col = collections.get(key)
        if not col:
            return ""
        data = col.get("data", {})
        name = str(data.get("name", "") or "")
        parent = str(data.get("parentCollection", "") or "")
        if parent:
            parent_path = self._collection_path(parent, collections, cache)
            path = f"{parent_path}/{name}" if parent_path else name
        else:
            path = name
        cache[key] = path
        return path

    def fetch_corpus(self, max_items: int = 2000) -> list[dict[str, Any]]:
        collections = self._fetch_collections()
        collection_path_cache: dict[str, str] = {}

        start = 0
        page_size = 100
        corpus: list[dict[str, Any]] = []

        while len(corpus) < max_items:
            batch = self._get("items", {"format": "json", "limit": page_size, "start": start})
            if not batch:
                break

            for raw in batch:
                data = raw.get("data", {})
                item_type = str(data.get("itemType", "") or "")
                abstract = str(data.get("abstractNote", "") or "").strip()
                title = str(data.get("title", "") or "").strip()

                if item_type not in _PAPER_TYPES:
                    continue
                if not abstract:
                    continue

                collection_keys = data.get("collections", []) or []
                paths = [
                    self._collection_path(str(col_key), collections, collection_path_cache)
                    for col_key in collection_keys
                ]
                paths = [p for p in paths if p]

                if self.include_path:
                    if not any(_match_any(path, self.include_path) for path in paths):
                        continue
                if self.ignore_path:
                    if any(_match_any(path, self.ignore_path) for path in paths):
                        continue

                corpus.append(
                    {
                        "title": title,
                        "abstract": abstract,
                        "paths": paths,
                    }
                )
                if len(corpus) >= max_items:
                    break

            if len(batch) < page_size:
                break
            start += len(batch)

        return corpus


def _build_idf(corpus_texts: list[str]) -> tuple[Counter[str], float]:
    doc_tokens = [set(_tokenize(text)) for text in corpus_texts if text.strip()]
    n_docs = len(doc_tokens)
    if n_docs == 0:
        return Counter(), 1.0

    df: Counter[str] = Counter()
    for tokens in doc_tokens:
        for tok in tokens:
            df[tok] += 1

    max_idf = max(math.log((n_docs + 1.0) / (freq + 1.0)) + 1.0 for freq in df.values())
    return df, max_idf


def _idf_similarity(tokens: set[str], df: Counter[str], n_docs: int, max_idf: float) -> float:
    if not tokens or n_docs == 0 or not df:
        return 0.0
    matched = 0.0
    for tok in tokens:
        freq = df.get(tok)
        if not freq:
            continue
        matched += math.log((n_docs + 1.0) / (freq + 1.0)) + 1.0
    denom = len(tokens) * max(max_idf, 1e-6)
    return min(max(matched / denom, 0.0), 1.0)


def _set_overlap_similarity(tokens: set[str], reference: set[str]) -> float:
    if not tokens or not reference:
        return 0.0
    inter = len(tokens & reference)
    return inter / max(len(tokens), 1)


def assist_recommendations_with_zotero(
    all_recs: dict[str, list[dict[str, Any]]],
    description_text: str,
    researcher_profile_path: str | None,
    user_id: str,
    api_key: str,
    include_path: list[str] | None = None,
    ignore_path: list[str] | None = None,
    weight: float = 1.5,
    top_k_per_source: int = 0,
    max_corpus_items: int = 2000,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    if not user_id:
        raise ValueError("Zotero user ID is required.")
    if not api_key:
        raise ValueError("Zotero API key is required.")

    client = ZoteroCorpusClient(
        user_id=user_id,
        api_key=api_key,
        include_path=include_path,
        ignore_path=ignore_path,
    )
    corpus = client.fetch_corpus(max_items=max_corpus_items)
    if not corpus:
        raise RuntimeError("No Zotero papers were fetched. Check user ID/API key and include/ignore path patterns.")

    corpus_texts = [f"{item['title']}\n{item['abstract']}" for item in corpus]
    df, max_idf = _build_idf(corpus_texts)
    n_docs = len(corpus_texts)

    profile_text = "\n".join([description_text.strip(), _read_text(researcher_profile_path)]).strip()
    profile_tokens = set(_tokenize(profile_text))

    updated: dict[str, list[dict[str, Any]]] = {}
    rec_count = 0

    for source_name, recs in all_recs.items():
        new_recs: list[dict[str, Any]] = []
        for rec in recs:
            text = _extract_text(rec)
            tokens = set(_tokenize(text))

            zotero_sim = _idf_similarity(tokens, df, n_docs, max_idf)
            profile_sim = _set_overlap_similarity(tokens, profile_tokens)
            assist_component = 0.7 * zotero_sim + 0.3 * profile_sim

            try:
                base_score = float(rec.get("score", 0) or 0)
            except (TypeError, ValueError):
                base_score = 0.0

            assisted_score = round(base_score + weight * assist_component, 4)
            merged = dict(rec)
            merged["score_before_assist"] = round(base_score, 4)
            merged["zotero_similarity"] = round(zotero_sim, 4)
            merged["profile_similarity"] = round(profile_sim, 4)
            merged["assist_boost"] = round(weight * assist_component, 4)
            merged["score"] = assisted_score
            merged["assisted_score"] = assisted_score
            new_recs.append(merged)
            rec_count += 1

        new_recs.sort(key=lambda item: float(item.get("score", 0) or 0), reverse=True)
        if top_k_per_source > 0:
            new_recs = new_recs[:top_k_per_source]
        updated[source_name] = new_recs

    stats = {
        "zotero_corpus_size": len(corpus),
        "recommendation_count": rec_count,
        "top_k_per_source": top_k_per_source,
        "weight": weight,
    }
    return updated, stats
