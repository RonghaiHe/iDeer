from __future__ import annotations

import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import MagicMock, patch


def _mock_response(data: bytes) -> MagicMock:
    resp = MagicMock()
    resp.read.return_value = data
    resp.__enter__.return_value = resp
    return resp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.zotero_assist import (
    ZoteroCorpusClient,
    _build_idf,
    _extract_text,
    _idf_similarity,
    _match_any,
    _read_text,
    _set_overlap_similarity,
    _tokenize,
    assist_recommendations_with_zotero,
)


# ──────────────────────────────────────────────
# Pure function: _tokenize
# ──────────────────────────────────────────────
class TokenizeTest(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(_tokenize(""), [])

    def test_lowercase(self):
        self.assertEqual(_tokenize("Hello World"), ["hello", "world"])

    def test_underscore_is_not_alphanumeric(self):
        self.assertEqual(_tokenize("foo-bar_baz!123"), ["foo", "bar", "baz", "123"])

    def test_whitespace_and_punctuation(self):
        self.assertEqual(_tokenize("a   b!!!c;;;d"), ["a", "b", "c", "d"])

    def test_mixed_case(self):
        self.assertEqual(_tokenize("LLM Agent SAFETY"), ["llm", "agent", "safety"])


# ──────────────────────────────────────────────
# Pure function: _read_text
# ──────────────────────────────────────────────
class ReadTextTest(unittest.TestCase):
    def test_none_path_returns_empty(self):
        self.assertEqual(_read_text(None), "")

    def test_non_existent_returns_empty(self):
        self.assertEqual(_read_text("/nonexistent/path/abc.md"), "")

    def test_reads_existing_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("researcher profile content")
            path = f.name
        try:
            self.assertEqual(_read_text(path), "researcher profile content")
        finally:
            Path(path).unlink(missing_ok=True)

    def test_strips_whitespace(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("  content with padding  \n")
            path = f.name
        try:
            self.assertEqual(_read_text(path), "content with padding")
        finally:
            Path(path).unlink(missing_ok=True)


# ──────────────────────────────────────────────
# Pure function: _match_any
# ──────────────────────────────────────────────
class MatchAnyTest(unittest.TestCase):
    def test_match_fnmatch(self):
        self.assertTrue(_match_any("2025/agents/survey", ["2025/*"]))

    def test_match_posix(self):
        self.assertTrue(_match_any("survey/safety/report", ["survey/**"]))

    def test_no_match(self):
        self.assertFalse(_match_any("2025/agents/survey", ["2026/*"]))

    def test_empty_patterns(self):
        self.assertFalse(_match_any("anything", []))

    def test_match_among_multiple(self):
        self.assertTrue(_match_any("data/safety", ["*data*", "safety*"]))

    def test_exact_match(self):
        self.assertTrue(_match_any("benchmark", ["benchmark"]))


# ──────────────────────────────────────────────
# Pure function: _extract_text
# ──────────────────────────────────────────────
class ExtractTextTest(unittest.TestCase):
    def test_all_fields_present(self):
        item = {"title": "T", "abstract": "A", "summary": "S"}
        self.assertEqual(_extract_text(item), "T\nA\nS")

    def test_missing_fields_fallback(self):
        item = {"title": "Only Title"}
        self.assertEqual(_extract_text(item), "Only Title\n\n")

    def test_none_values(self):
        item = {"title": None, "abstract": "Abstract", "summary": None}
        self.assertEqual(_extract_text(item), "\nAbstract\n")

    def test_empty_dict(self):
        self.assertEqual(_extract_text({}), "\n\n")


# ──────────────────────────────────────────────
# Pure function: _build_idf
# ──────────────────────────────────────────────
class BuildIdfTest(unittest.TestCase):
    def test_empty_corpus(self):
        df, max_idf = _build_idf([])
        self.assertEqual(df, Counter())
        self.assertEqual(max_idf, 1.0)

    def test_single_document(self):
        df, max_idf = _build_idf(["cat dog"])
        self.assertEqual(df, Counter({"cat": 1, "dog": 1}))
        self.assertGreater(max_idf, 0)

    def test_multiple_documents(self):
        df, max_idf = _build_idf(["cat dog", "dog fish", "cat fish"])
        self.assertEqual(df["cat"], 2)
        self.assertEqual(df["dog"], 2)
        self.assertEqual(df["fish"], 2)
        self.assertGreater(max_idf, 0)

    def test_repeated_tokens_in_doc_count_once(self):
        df, _ = _build_idf(["cat cat cat"])
        self.assertEqual(df["cat"], 1)


# ──────────────────────────────────────────────
# Pure function: _idf_similarity
# ──────────────────────────────────────────────
class IdfSimilarityTest(unittest.TestCase):
    def test_empty_tokens_returns_zero(self):
        self.assertEqual(_idf_similarity(set(), Counter({"a": 1}), 1, 1.0), 0.0)

    def test_empty_df_returns_zero(self):
        self.assertEqual(_idf_similarity({"a"}, Counter(), 1, 1.0), 0.0)

    def test_zero_n_docs_returns_zero(self):
        self.assertEqual(_idf_similarity({"a"}, Counter({"a": 1}), 0, 1.0), 0.0)

    def test_perfect_match_gives_max_score(self):
        df, max_idf = _build_idf(["rare token"])
        tokens = {"rare", "token"}
        score = _idf_similarity(tokens, df, 1, max_idf)
        self.assertAlmostEqual(score, 1.0, places=4)

    def test_no_overlap_returns_zero(self):
        df = Counter({"cat": 1})
        score = _idf_similarity({"zzz"}, df, 5, 2.0)
        self.assertAlmostEqual(score, 0.0, places=4)

    def test_partial_overlap(self):
        df = Counter({"cat": 1, "dog": 1, "unrelated": 3})
        score = _idf_similarity({"cat", "dog", "other"}, df, 5, 3.0)
        self.assertGreater(score, 0.0)
        self.assertLess(score, 1.0)


# ──────────────────────────────────────────────
# Pure function: _set_overlap_similarity
# ──────────────────────────────────────────────
class SetOverlapSimilarityTest(unittest.TestCase):
    def test_empty_tokens_returns_zero(self):
        self.assertEqual(_set_overlap_similarity(set(), {"a"}), 0.0)

    def test_empty_reference_returns_zero(self):
        self.assertEqual(_set_overlap_similarity({"a"}, set()), 0.0)

    def test_full_overlap(self):
        self.assertEqual(_set_overlap_similarity({"cat", "dog"}, {"dog", "cat"}), 1.0)

    def test_no_overlap(self):
        self.assertEqual(_set_overlap_similarity({"cat"}, {"dog"}), 0.0)

    def test_partial_overlap(self):
        self.assertAlmostEqual(_set_overlap_similarity({"cat", "dog"}, {"cat"}), 1 / 2)

    def test_overlap_with_larger_query(self):
        self.assertAlmostEqual(_set_overlap_similarity({"a", "b", "c"}, {"a"}), 1 / 3)


# ──────────────────────────────────────────────
# ZoteroCorpusClient._collection_path (pure)
# ──────────────────────────────────────────────
class CollectionPathTest(unittest.TestCase):
    def test_top_level(self):
        collections = {"abc": {"data": {"name": "2025"}}}
        client = ZoteroCorpusClient("id", "key")
        path = client._collection_path("abc", collections, {})
        self.assertEqual(path, "2025")

    def test_nested(self):
        collections = {
            "parent": {"data": {"name": "papers"}},
            "child": {"data": {"name": "agents", "parentCollection": "parent"}},
        }
        client = ZoteroCorpusClient("id", "key")
        path = client._collection_path("child", collections, {})
        self.assertEqual(path, "papers/agents")

    def test_double_nested(self):
        collections = {
            "root": {"data": {"name": "Lab"}},
            "mid": {"data": {"name": "2025", "parentCollection": "root"}},
            "leaf": {"data": {"name": "Safety", "parentCollection": "mid"}},
        }
        client = ZoteroCorpusClient("id", "key")
        path = client._collection_path("leaf", collections, {})
        self.assertEqual(path, "Lab/2025/Safety")

    def test_unknown_key_returns_empty(self):
        collections = {}
        client = ZoteroCorpusClient("id", "key")
        path = client._collection_path("nope", collections, {})
        self.assertEqual(path, "")

    def test_uses_cache(self):
        collections = {"abc": {"data": {"name": "papers"}}}
        client = ZoteroCorpusClient("id", "key")
        cache = {"abc": "cached/value"}
        path = client._collection_path("abc", collections, cache)
        self.assertEqual(path, "cached/value")


# ──────────────────────────────────────────────
# ZoteroCorpusClient._get (network)
# ──────────────────────────────────────────────
class ZoteroClientGetTest(unittest.TestCase):
    def test_success_returns_parsed_list(self):
        client = ZoteroCorpusClient("uid", "apikey")

        with patch("core.zotero_assist.urlopen", return_value=_mock_response(b'[{"key": "abc"}]')) as urlopen:
            result = client._get("items", {"limit": 10})

        self.assertEqual(result, [{"key": "abc"}])
        urlopen.assert_called_once()
        args, _ = urlopen.call_args
        req = args[0]
        self.assertIn("api.zotero.org/users/uid/items", req.full_url)
        self.assertIn("limit=10", req.full_url)
        self.assertEqual(req.get_header("Zotero-api-key"), "apikey")

    def test_non_list_response_returns_empty(self):
        client = ZoteroCorpusClient("uid", "apikey")

        with patch("core.zotero_assist.urlopen", return_value=_mock_response(b'{"totalResults": 0}')):
            result = client._get("items")

        self.assertEqual(result, [])

    def test_path_no_params(self):
        client = ZoteroCorpusClient("uid", "apikey")

        with patch("core.zotero_assist.urlopen", return_value=_mock_response(b"[]")) as urlopen:
            client._get("collections")

        urlopen.assert_called_once()
        req = urlopen.call_args[0][0]
        self.assertIn("/users/uid/collections", req.full_url)
        self.assertNotIn("?", req.full_url)

    def test_timeout_passed(self):
        client = ZoteroCorpusClient("uid", "apikey", timeout_seconds=5)

        with patch("core.zotero_assist.urlopen", return_value=_mock_response(b"[]")) as urlopen:
            client._get("items", {"format": "json"})

        _, kwargs = urlopen.call_args
        self.assertEqual(kwargs["timeout"], 5)


# ──────────────────────────────────────────────
# ZoteroCorpusClient._fetch_collections
# ──────────────────────────────────────────────
class FetchCollectionsTest(unittest.TestCase):
    def test_single_page(self):
        client = ZoteroCorpusClient("uid", "key")

        with patch("core.zotero_assist.urlopen", return_value=_mock_response(b'[{"key": "abc"}, {"key": "def"}]')) as urlopen:
            result = client._fetch_collections()

        self.assertEqual(set(result.keys()), {"abc", "def"})
        urlopen.assert_called_once()

    def test_pagination(self):
        client = ZoteroCorpusClient("uid", "key")

        with patch("core.zotero_assist.urlopen", side_effect=[
            _mock_response(json.dumps([{"key": f"k{i}"} for i in range(100)]).encode()),
            _mock_response(b'[{"key": "k100"}, {"key": "k101"}]'),
        ]) as urlopen:
            result = client._fetch_collections()

        self.assertEqual(len(result), 102)
        self.assertIn("k0", result)
        self.assertIn("k101", result)
        self.assertEqual(urlopen.call_count, 2)

    def test_empty_response(self):
        client = ZoteroCorpusClient("uid", "key")

        with patch("core.zotero_assist.urlopen", return_value=_mock_response(b"[]")):
            result = client._fetch_collections()

        self.assertEqual(result, {})


# ──────────────────────────────────────────────
# ZoteroCorpusClient.fetch_corpus
# ──────────────────────────────────────────────
class FetchCorpusTest(unittest.TestCase):
    def _make_item(self, key: str, item_type: str, title: str, abstract: str, collections: list[str] | None = None):
        return {
            "key": key,
            "data": {
                "key": key,
                "itemType": item_type,
                "title": title,
                "abstractNote": abstract,
                "collections": collections or [],
            },
        }

    def _build_collections(self, items: list[dict], col_defs: dict[str, str] | None = None) -> bytes:
        if col_defs is None:
            return b"[]"
        payload = [{"key": k, "data": {"key": k, "name": v, "parentCollection": False}} for k, v in col_defs.items()]
        return json.dumps(payload).encode()

    def _mock_item_responses(self, col_bytes: bytes, item_bytes: bytes) -> list[MagicMock]:
        return [_mock_response(col_bytes), _mock_response(item_bytes)]

    def test_filters_non_paper_types(self):
        client = ZoteroCorpusClient("uid", "key")
        items = [
            self._make_item("1", "journalArticle", "Paper", "Has abstract"),
            self._make_item("2", "note", "Note", "Should be skipped"),
            self._make_item("3", "attachment", "PDF", "Should be skipped"),
        ]

        with patch("core.zotero_assist.urlopen", side_effect=self._mock_item_responses(b"[]", json.dumps(items).encode())):
            corpus = client.fetch_corpus(max_items=100)

        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0]["title"], "Paper")

    def test_skips_items_without_abstract(self):
        client = ZoteroCorpusClient("uid", "key")
        items = [
            self._make_item("1", "conferencePaper", "Has Abstract", "Real abstract here"),
            self._make_item("2", "journalArticle", "No Abstract", ""),
        ]

        with patch("core.zotero_assist.urlopen", side_effect=self._mock_item_responses(b"[]", json.dumps(items).encode())):
            corpus = client.fetch_corpus(max_items=100)

        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0]["title"], "Has Abstract")

    def test_include_path_filter(self):
        client = ZoteroCorpusClient("uid", "key", include_path=["2025*"])
        collections = {"col1": {"key": "col1", "data": {"key": "col1", "name": "2025", "parentCollection": False}}}

        with patch("core.zotero_assist.urlopen", side_effect=[
            _mock_response(json.dumps([collections["col1"]]).encode()),
            _mock_response(json.dumps([
                self._make_item("1", "conferencePaper", "In 2025", "abstract", collections=["col1"]),
                self._make_item("2", "preprint", "Not included", "abstract", collections=["col_other"]),
            ]).encode()),
        ]):
            corpus = client.fetch_corpus(max_items=100)

        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0]["title"], "In 2025")

    def test_ignore_path_filter(self):
        client = ZoteroCorpusClient("uid", "key", ignore_path=["archived*"])
        collections = {
            "active_col": {"key": "active", "data": {"key": "active", "name": "active", "parentCollection": False}},
            "archived_col": {"key": "arch", "data": {"key": "arch", "name": "archived", "parentCollection": False}},
        }

        with patch("core.zotero_assist.urlopen", side_effect=[
            _mock_response(json.dumps(list(collections.values())).encode()),
            _mock_response(json.dumps([
                self._make_item("1", "conferencePaper", "Active", "abstract", collections=["active"]),
                self._make_item("2", "journalArticle", "Archived", "abstract", collections=["arch"]),
            ]).encode()),
        ]):
            corpus = client.fetch_corpus(max_items=100)

        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0]["title"], "Active")

    def test_max_items_respected(self):
        client = ZoteroCorpusClient("uid", "key")
        items = [self._make_item(str(i), "journalArticle", f"Paper {i}", "has abstract") for i in range(200)]

        with patch("core.zotero_assist.urlopen", side_effect=self._mock_item_responses(b"[]", json.dumps(items).encode())):
            corpus = client.fetch_corpus(max_items=5)

        self.assertEqual(len(corpus), 5)

    def test_corpus_includes_collection_paths(self):
        client = ZoteroCorpusClient("uid", "key")
        collections = {"col1": {"key": "col1", "data": {"key": "col1", "name": "papers", "parentCollection": False}}}

        with patch("core.zotero_assist.urlopen", side_effect=[
            _mock_response(json.dumps([collections["col1"]]).encode()),
            _mock_response(json.dumps([self._make_item("1", "journalArticle", "Has Path", "abstract", collections=["col1"])]).encode()),
        ]):
            corpus = client.fetch_corpus(max_items=100)

        self.assertEqual(len(corpus), 1)
        self.assertEqual(corpus[0]["paths"], ["papers"])

    def test_empty_corpus_when_no_matching_items(self):
        client = ZoteroCorpusClient("uid", "key", include_path=["nonexistent/**"])
        collections = {"c1": {"key": "c1", "data": {"key": "c1", "name": "papers", "parentCollection": False}}}

        with patch("core.zotero_assist.urlopen", side_effect=[
            _mock_response(json.dumps([collections["c1"]]).encode()),
            _mock_response(json.dumps([self._make_item("1", "journalArticle", "Paper", "abstract", collections=["c1"])]).encode()),
        ]):
            corpus = client.fetch_corpus(max_items=100)

        self.assertEqual(corpus, [])


# ──────────────────────────────────────────────
# assist_recommendations_with_zotero (main entry)
# ──────────────────────────────────────────────
class AssistRecommendationsTest(unittest.TestCase):
    def setUp(self):
        self.sample_recs = {
            "arxiv": [
                {"title": "Agent Safety", "abstract": "AI safety agent alignment.", "score": 8.0},
                {"title": "Vision Model", "abstract": "Computer vision models.", "score": 5.0},
            ],
            "huggingface": [
                {"title": "Benchmark Design", "abstract": "Evaluation benchmark methodology.", "score": 7.5},
            ],
        }

        self.sample_corpus = [
            {"title": "Safety Alignment", "abstract": "Alignment safety in AI agents.", "paths": ["2025"]},
            {"title": "Model Robustness", "abstract": "Robustness in vision models.", "paths": ["2025"]},
        ]

        self.profile_content = "I research AI safety and agent alignment."

    def test_missing_user_id_raises(self):
        with self.assertRaises(ValueError):
            assist_recommendations_with_zotero(
                all_recs={},
                description_text="",
                researcher_profile_path=None,
                user_id="",
                api_key="valid",
            )

    def test_missing_api_key_raises(self):
        with self.assertRaises(ValueError):
            assist_recommendations_with_zotero(
                all_recs={},
                description_text="",
                researcher_profile_path=None,
                user_id="valid",
                api_key="",
            )

    def test_empty_corpus_raises(self):
        with (
            patch.object(ZoteroCorpusClient, "fetch_corpus", return_value=[]),
        ):
            with self.assertRaises(RuntimeError):
                assist_recommendations_with_zotero(
                    all_recs=self.sample_recs,
                    description_text="AI safety",
                    researcher_profile_path=None,
                    user_id="uid",
                    api_key="key",
                )

    def test_normal_flow_returns_updated_recs_and_stats(self):
        with (
            patch.object(ZoteroCorpusClient, "fetch_corpus", return_value=self.sample_corpus),
            patch("core.zotero_assist._read_text", return_value=self.profile_content),
        ):
            updated, stats = assist_recommendations_with_zotero(
                all_recs=self.sample_recs,
                description_text="AI agent safety",
                researcher_profile_path="/fake/path.md",
                user_id="uid",
                api_key="key",
                weight=1.0,
                top_k_per_source=0,
                max_corpus_items=2000,
            )

        self.assertEqual(set(updated.keys()), {"arxiv", "huggingface"})
        self.assertEqual(len(updated["arxiv"]), 2)
        self.assertEqual(len(updated["huggingface"]), 1)

        first = updated["arxiv"][0]
        self.assertIn("score_before_assist", first)
        self.assertIn("zotero_similarity", first)
        self.assertIn("profile_similarity", first)
        self.assertIn("assist_boost", first)
        self.assertIn("assisted_score", first)
        self.assertGreater(first["score"], 8.0)

        self.assertEqual(stats["zotero_corpus_size"], 2)
        self.assertEqual(stats["recommendation_count"], 3)
        self.assertEqual(stats["top_k_per_source"], 0)
        self.assertEqual(stats["weight"], 1.0)

    def test_top_k_truncation_per_source(self):
        with (
            patch.object(ZoteroCorpusClient, "fetch_corpus", return_value=self.sample_corpus),
            patch("core.zotero_assist._read_text", return_value=self.profile_content),
        ):
            updated, _ = assist_recommendations_with_zotero(
                all_recs=self.sample_recs,
                description_text="AI agent safety",
                researcher_profile_path=None,
                user_id="uid",
                api_key="key",
                top_k_per_source=1,
            )

        self.assertEqual(len(updated["arxiv"]), 1)
        self.assertEqual(len(updated["huggingface"]), 1)

    def test_recs_sorted_by_score_descending(self):
        with (
            patch.object(ZoteroCorpusClient, "fetch_corpus", return_value=self.sample_corpus),
            patch("core.zotero_assist._read_text", return_value=self.profile_content),
        ):
            updated, _ = assist_recommendations_with_zotero(
                all_recs=self.sample_recs,
                description_text="AI agent safety",
                researcher_profile_path=None,
                user_id="uid",
                api_key="key",
                weight=2.0,
            )

        scores = [r["score"] for r in updated["arxiv"]]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_profile_path_not_exist_falls_back_to_description(self):
        non_existent = str(ROOT / "_nonexistent_profile_xxx.md")
        with (
            patch.object(ZoteroCorpusClient, "fetch_corpus", return_value=self.sample_corpus),
        ):
            updated, _ = assist_recommendations_with_zotero(
                all_recs={"arxiv": self.sample_recs["arxiv"]},
                description_text="AI agent safety",
                researcher_profile_path=non_existent,
                user_id="uid",
                api_key="key",
            )

        self.assertEqual(len(updated["arxiv"]), 2)

    def test_score_handles_none_values_gracefully(self):
        recs_with_none = {
            "arxiv": [
                {"title": "Paper", "abstract": "text", "score": None},
            ]
        }
        with (
            patch.object(ZoteroCorpusClient, "fetch_corpus", return_value=self.sample_corpus),
            patch("core.zotero_assist._read_text", return_value=""),
        ):
            updated, _ = assist_recommendations_with_zotero(
                all_recs=recs_with_none,
                description_text="AI",
                researcher_profile_path=None,
                user_id="uid",
                api_key="key",
            )

        self.assertEqual(updated["arxiv"][0]["score_before_assist"], 0.0)


if __name__ == "__main__":
    unittest.main()
