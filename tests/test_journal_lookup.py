import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

"""
python -m unittest tests.test_journal_lookup.JournalLookupTest -v
"""

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class JournalLookupTest(unittest.TestCase):
    def test_load_registry(self):
        from core.journal_lookup import load_registry

        registry = load_registry()
        self.assertIn("IEEE TRO", registry)
        self.assertIn("IJRR", registry)
        self.assertEqual(registry["IEEE TRO"]["issn"], "1552-3098")

    def test_search_exact_key(self):
        from core.journal_lookup import load_registry, search

        registry = load_registry()
        result = search("IEEE TRO", registry)
        self.assertIsNotNone(result)
        key, entry = result
        self.assertEqual(key, "IEEE TRO")
        self.assertIn("Robotics", entry["full_name"])

    def test_search_case_insensitive(self):
        from core.journal_lookup import load_registry, search

        registry = load_registry()
        result = search("ieee tro", registry)
        self.assertIsNotNone(result)
        key, _ = result
        self.assertEqual(key, "IEEE TRO")

    def test_search_by_full_name(self):
        from core.journal_lookup import load_registry, search

        registry = load_registry()
        result = search("Automatica", registry)
        self.assertIsNotNone(result)
        key, entry = result
        self.assertEqual(key, "Automatica")

    def test_search_not_found(self):
        from core.journal_lookup import load_registry, search

        registry = load_registry()
        result = search("Nonexistent Journal", registry)
        self.assertIsNone(result)

    def test_resolve_urls(self):
        from core.journal_lookup import load_registry, resolve_urls

        registry = load_registry()
        urls = resolve_urls(["IEEE TRO", "IJRR"], registry)
        self.assertEqual(len(urls), 2)
        self.assertIn("ieeexplore.ieee.org", urls[0])
        self.assertIn("acm.org", urls[1])

    def test_resolve_urls_skips_null(self):
        from core.journal_lookup import load_registry, resolve_urls

        registry = load_registry()
        urls = resolve_urls(["IROS", "IEEE CDC"], registry)
        self.assertEqual(len(urls), 0)

    def test_resolve_urls_unknown_skipped(self):
        from core.journal_lookup import load_registry, resolve_urls

        registry = load_registry()
        urls = resolve_urls(["IEEE TRO", "Unknown Journal"], registry)
        self.assertEqual(len(urls), 1)

    def test_resolve_from_env(self):
        from core.journal_lookup import resolve_from_env

        urls = resolve_from_env("IEEE TRO|IJRR")
        self.assertEqual(len(urls), 2)

    def test_resolve_from_env_comma(self):
        from core.journal_lookup import resolve_from_env

        urls = resolve_from_env("IEEE TRO, IJRR")
        self.assertEqual(len(urls), 2)

    def test_resolve_from_env_empty(self):
        from core.journal_lookup import resolve_from_env

        urls = resolve_from_env("")
        self.assertEqual(len(urls), 0)

    def test_search_custom_registry(self):
        from core.journal_lookup import search

        custom = {
            "My Journal": {
                "full_name": "My Custom Journal",
                "rss_url": "https://example.com/rss.xml",
                "publisher": "Test",
                "issn": "1234-5678",
            }
        }
        result = search("My Journal", custom)
        self.assertIsNotNone(result)
        key, entry = result
        self.assertEqual(entry["rss_url"], "https://example.com/rss.xml")


class RssSourceJournalIntegrationTest(unittest.TestCase):
    def test_extract_args_includes_journals(self):
        from sources.rss_source import RssSource

        parser = argparse.ArgumentParser()
        RssSource.add_arguments(parser)
        args = parser.parse_args(["--rss_journals", "IEEE TRO", "IJRR"])
        extracted = RssSource.extract_args(args)
        self.assertEqual(extracted["journal_names"], ["IEEE TRO", "IJRR"])

    def test_extract_args_journals_from_env(self):
        from sources.rss_source import RssSource

        parser = argparse.ArgumentParser()
        RssSource.add_arguments(parser)
        args = parser.parse_args([])
        with patch.dict("os.environ", {"RSS_JOURNALS": "IEEE TRO IJRR"}):
            extracted = RssSource.extract_args(args)
            self.assertEqual(extracted["journal_names"], ["IEEE TRO", "IJRR"])


if __name__ == "__main__":
    unittest.main()
