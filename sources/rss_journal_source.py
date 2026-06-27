import argparse
import hashlib
import json
import os
from urllib.parse import quote

from core.config import LLMConfig, CommonConfig
from core.journal_lookup import resolve_urls, load_registry
from email_utils.base_template import get_stars
from email_utils.rss_journal_template import get_journal_paper_block_html
from fetchers.rss_fetcher import fetch_rss_feeds
from sources.base import BaseSource


class RssJournalSource(BaseSource):
    name = "rss_journals"
    default_title = "Journal RSS Daily"

    def __init__(self, source_args: dict, llm_config: LLMConfig, common_config: CommonConfig):
        super().__init__(source_args, llm_config, common_config)
        self.max_items = source_args.get("max_items", 30)

        journal_names = source_args.get("journal_names") or []
        self.urls = resolve_urls(journal_names) if journal_names else []
        if not self.urls:
            print(f"[{self.name}] No journal URLs resolved — source will produce no items.")

        registry = load_registry()
        self._url_to_journal: dict[str, tuple[str, dict]] = {}
        for key, entry in registry.items():
            rss_url = (entry.get("rss_url") or "").strip()
            if rss_url:
                self._url_to_journal[rss_url.lower()] = (key, entry)

        url_sig = hashlib.sha256("|".join(sorted(self.urls)).encode()).hexdigest()[:10]
        cache_key = f"items_{url_sig}_{self.max_items}"
        cached = self._load_fetch_cache(cache_key)
        if cached is not None:
            self.items = cached
        else:
            self.items = fetch_rss_feeds(self.urls, max_items=self.max_items)
            if self.items:
                self._save_fetch_cache(cache_key, self.items)

    @staticmethod
    def add_arguments(parser: argparse.ArgumentParser):
        parser.add_argument(
            "--rss_journals_names", nargs="+", default=None,
            help="[RSS Journals] Journal names to subscribe (resolved via data/journal_rss.json). "
                 "If not provided, reads from RSS_JOURNALS env var.",
        )
        parser.add_argument(
            "--rss_journals_max_items", type=int,
            default=int(os.getenv("RSS_JOURNAL_MAX_ITEMS", "50")),
            help="[RSS Journals] Max items to fetch and recommend",
        )

    @staticmethod
    def extract_args(args) -> dict:
        journal_names = getattr(args, "rss_journals_names", None)
        if not journal_names:
            raw = os.getenv("RSS_JOURNALS", "")
            if raw.strip():
                if "|" in raw:
                    journal_names = [n.strip() for n in raw.split("|") if n.strip()]
                elif "," in raw:
                    journal_names = [n.strip() for n in raw.split(",") if n.strip()]
                else:
                    journal_names = [n.strip() for n in raw.split() if n.strip()]
        return {
            "journal_names": journal_names or [],
            "max_items": args.rss_journals_max_items,
        }

    def fetch_items(self) -> list[dict]:
        print(f"[{self.name}] {len(self.items)} journal RSS items available")
        return self.items

    def get_item_cache_id(self, item: dict) -> str:
        return item.get("cache_id", "rss_journal_unknown")

    def get_max_items(self) -> int:
        return self.max_items

    def build_eval_prompt(self, item: dict) -> str:
        summary = item.get("summary") or item.get("abstract") or "No summary available."
        if len(summary) > 1200:
            summary = summary[:1197] + "..."
        authors = item.get("authors", "")
        authors_line = f"作者: {authors}\n" if authors else ""
        return f"""你是一个有帮助的信息筛选助手，可以帮助我构建每日 AI 信息源摘要。
以下是我最近研究领域的描述：
{self.description}

以下是来自期刊 RSS 订阅的论文：
来源: {item.get('source_label', 'Journal RSS')}
标题: {item.get('title', '')}
{authors_line}发布时间: {item.get('published_at', '')}
内容: {summary}

1. 用中文总结这条信息的主要内容。
2. 请评估这条信息与我研究领域的相关性，并给出 0-10 的评分。其中 0 表示完全不相关，10 表示高度相关。

请按以下 JSON 格式给出你的回答：
{{
    "summary": "一段纯文本的中文总结（不要嵌套JSON/dict，直接写一段话）",
    "relevance": <你的评分>
}}
重要：summary 必须是一段纯文本字符串，不要返回嵌套的 JSON 对象或字典。
使用中文回答。
直接返回上述 JSON 格式，无需任何额外解释。"""

    def parse_eval_response(self, item: dict, response: str) -> dict:
        response = response.strip("```").strip("json")
        data = json.loads(response)

        feed_url = item.get("feed_url", "")
        journal_name = item.get("source_label", "Journal RSS")
        journal_full_name = ""
        if feed_url:
            match = self._url_to_journal.get(feed_url.strip().lower())
            if match:
                journal_name = match[0]
                journal_full_name = match[1].get("full_name", "")

        return {
            "title": item.get("title", "Untitled"),
            "summary": self._ensure_str(data["summary"]),
            "score": float(data["relevance"]),
            "url": item.get("url", ""),
            "abstract": item.get("abstract", ""),
            "published_at": item.get("published_at", ""),
            "feed_url": feed_url,
            "source_label": item.get("source_label", "Journal RSS"),
            "journal_name": journal_name,
            "journal_full_name": journal_full_name,
            "authors": item.get("authors", ""),
        }

    def render_item_html(self, item: dict) -> str:
        rate = get_stars(item.get("score", 0))
        title = item.get("title", "Untitled")
        summary = item.get("summary", "")
        url = item.get("url", "")
        journal_name = item.get("journal_name", item.get("source_label", "Journal RSS"))
        journal_full_name = item.get("journal_full_name", "")
        published_at = item.get("published_at", "")
        authors = item.get("authors", "")

        zotero_save = f"https://www.zotero.org/save/?q={quote(url, safe='')}" if url else ""

        return get_journal_paper_block_html(
            title=title,
            rate=rate,
            journal_name=journal_name,
            journal_full_name=journal_full_name,
            published_at=published_at,
            summary=summary,
            paper_url=url,
            zotero_save_url=zotero_save,
            authors=authors,
        )

    def get_theme_color(self) -> str:
        return "5,150,105"

    def get_section_header(self) -> str:
        return '<div class="section-title" style="border-bottom-color: #059669;">📚 Journal RSS</div>'

    def build_summary_overview(self, recommendations: list[dict]) -> str:
        lines = []
        for i, r in enumerate(recommendations):
            lines.append(
                f"{i + 1}. {r.get('title', 'Untitled')} "
                f"({r.get('source_label', 'Journal RSS')}) - Score: {r.get('score', 0)} - {r.get('summary', '')}"
            )
        return "\n".join(lines)

    def get_summary_prompt_template(self) -> str:
        return """
            请直接输出一段 HTML 片段，严格遵循以下结构，不要包含 JSON、Markdown 或多余说明：
            <div class="summary-wrapper">
              <div class="summary-section">
                <h2>今日期刊 RSS 动态</h2>
                <p>概括今天期刊 RSS 订阅里最值得关注的趋势...</p>
              </div>
              <div class="summary-section">
                <h2>重点推荐</h2>
                <ol class="summary-list">
                  <li class="summary-item">
                    <div class="summary-item__header"><span class="summary-item__title">论文标题</span><span class="summary-pill">期刊</span></div>
                    <p><strong>推荐理由：</strong>...</p>
                    <p><strong>关键内容：</strong>...</p>
                  </li>
                </ol>
              </div>
              <div class="summary-section">
                <h2>补充观察</h2>
                <p>其他值得持续关注的方向...</p>
              </div>
            </div>

            用中文撰写内容，重点推荐部分建议返回 3-5 条信息。
        """
