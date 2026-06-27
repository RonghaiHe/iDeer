"""Journal name to RSS feed URL lookup module."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT

_DEFAULT_REGISTRY_PATH = PROJECT_ROOT / "data" / "journal_rss.json"


def load_registry(path: str | Path | None = None) -> dict[str, Any]:
    """Load the journal RSS registry from a JSON file."""
    registry_path = Path(path) if path else _DEFAULT_REGISTRY_PATH
    if not registry_path.exists():
        print(f"[journal_lookup] Registry not found: {registry_path}")
        return {}
    with open(registry_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("journals", {})


def search(query: str, registry: dict[str, Any] | None = None) -> tuple[str, dict] | None:
    """Exact match a journal name (case-insensitive) against the registry.

    Matches against both the key and the ``full_name`` field.

    Returns:
        (key, entry) tuple if found, otherwise None.
    """
    if registry is None:
        registry = load_registry()
    query_lower = query.strip().lower()
    for key, entry in registry.items():
        if key.lower() == query_lower:
            return key, entry
        if entry.get("full_name", "").lower() == query_lower:
            return key, entry
    return None


def search_by_feed_url(feed_url: str, registry: dict[str, Any] | None = None) -> tuple[str, dict] | None:
    """Match a feed URL against the registry and return (key, entry) if found."""
    if registry is None:
        registry = load_registry()
    feed_lower = feed_url.strip().lower()
    for key, entry in registry.items():
        rss_url = (entry.get("rss_url") or "").strip().lower()
        if rss_url and rss_url == feed_lower:
            return key, entry
    return None


def resolve_urls(journal_names: list[str], registry: dict[str, Any] | None = None) -> list[str]:
    """Resolve a list of journal names to RSS feed URLs.

    Journals whose ``rss_url`` is ``null`` are skipped with a warning.
    """
    if registry is None:
        registry = load_registry()
    urls: list[str] = []
    for name in journal_names:
        result = search(name, registry)
        if result is None:
            print(f"[journal_lookup] Unknown journal: {name}")
            continue
        key, entry = result
        rss_url = entry.get("rss_url")
        if not rss_url:
            full_name = entry.get("full_name", key)
            print(f"[journal_lookup] No RSS feed available for {full_name}")
            continue
        urls.append(rss_url)
    return urls


def resolve_from_env(env_value: str | None = None) -> list[str]:
    """Read journal names from the ``RSS_JOURNALS`` env var and resolve URLs.

    Journal names can be separated by ``|`` (pipe) or ``,`` (comma).
    Space-separated single-word names are also supported.
    """
    raw = env_value if env_value is not None else os.getenv("RSS_JOURNALS", "")
    if not raw.strip():
        return []
    if "|" in raw:
        names = [n.strip() for n in raw.split("|") if n.strip()]
    elif "," in raw:
        names = [n.strip() for n in raw.split(",") if n.strip()]
    else:
        names = [n.strip() for n in raw.split() if n.strip()]
    if not names:
        return []
    return resolve_urls(names)


def list_all(registry: dict[str, Any] | None = None) -> None:
    """Print all registered journals and their RSS status."""
    if registry is None:
        registry = load_registry()
    if not registry:
        print("No journals registered.")
        return
    for key, entry in registry.items():
        rss_url = entry.get("rss_url")
        status = "OK" if rss_url else "NO RSS"
        full_name = entry.get("full_name", "")
        print(f"  {key:<20s} [{status}] {full_name}")
        if rss_url:
            print(f"  {'':20s} {rss_url}")


if __name__ == "__main__":
    import sys

    if "--list" in sys.argv:
        print("Available journals:")
        print("=" * 60)
        list_all()
    elif len(sys.argv) > 1:
        names = sys.argv[1:]
        urls = resolve_urls(names)
        for name, url in zip(names, urls):
            print(f"{name} -> {url}")
    else:
        print("Usage: python -m core.journal_lookup --list")
        print("       python -m core.journal_lookup <journal_name> [journal_name ...]")
