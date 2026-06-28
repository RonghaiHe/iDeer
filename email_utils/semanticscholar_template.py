import base64
from pathlib import Path

_brand_dir = Path(__file__).resolve().parent.parent / "docs" / "brand"

with open(_brand_dir / "alphaxiv.png", "rb") as f:
    _alphaxiv_logo_src = "data:image/png;base64," + base64.b64encode(f.read()).decode()

with open(_brand_dir / "zotero.png", "rb") as f:
    _zotero_logo_src = "data:image/png;base64," + base64.b64encode(f.read()).decode()

_icon_style = "height:14px;vertical-align:middle;margin-right:4px;"
_icon_style_zotero = "height:14px;vertical-align:middle;margin-right:4px;"


def get_paper_block_html(
    title: str,
    rate: str,
    authors: str,
    venue: str,
    venue_type: str,
    year: str,
    citations: int,
    summary: str,
    paper_url: str,
    zotero_save_url: str = "",
    arxiv_id: str = "",
    github_issue_url: str = "",
) -> str:
    venue_label = f" ({venue_type})" if venue_type else ""
    venue_line = f"<strong>Venue:</strong> {venue}{venue_label}" if venue else ""
    zotero_btn = ""
    if zotero_save_url:
        zotero_btn = (
            f'<a href="{zotero_save_url}" '
            f'style="display:inline-block;text-decoration:none;font-size:14px;'
            f'font-weight:bold;color:#fff;background-color:#6c3ec1;'
            f'padding:8px 16px;border-radius:6px;margin-left:8px;">'
            f'<img src="{_zotero_logo_src}" style="{_icon_style_zotero}" alt="">Save to Zotero</a>'
        )
    alphaxiv_btn = ""
    if arxiv_id:
        alphaxiv_btn = (
            f'<a href="https://www.alphaxiv.org/abs/{arxiv_id}" '
            f'style="display:inline-block;text-decoration:none;font-size:14px;'
            f'font-weight:bold;color:#fff;background-color:#6c3ec1;'
            f'padding:8px 16px;border-radius:6px;margin-left:8px;">'
            f'<img src="{_alphaxiv_logo_src}" style="{_icon_style}" alt="">AlphaXiv</a>'
        )
    github_btn = ""
    if github_issue_url:
        github_btn = (
            '<a href="{url}" '
            'style="display:inline-block;text-decoration:none;font-size:14px;'
            'font-weight:bold;color:#fff;background-color:#6c3ec1;'
            'padding:8px 16px;border-radius:6px;margin-left:8px;">'
            '\U0001f4da Add to Online Paper Reader</a>'.format(url=github_issue_url)
        )
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%%"
           style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px;
                  padding: 16px; background-color: #f5f0ff;">
    <tr>
        <td style="font-size: 20px; font-weight: bold; color: #333;">
            {title}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>Relevance:</strong> {rate}
        </td>
    </tr>
    <tr>
        <td style="font-size: 13px; color: #57606a; padding: 4px 0;">
            {authors} · {year} · Citations: {citations}
        </td>
    </tr>
    {venue_row}
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {summary}
        </td>
    </tr>
    <tr>
        <td style="padding: 8px 0;">
            <a href="{paper_url}"
               style="display: inline-block; text-decoration: none; font-size: 14px;
                      font-weight: bold; color: #fff; background-color: #6c3ec1;
                      padding: 8px 16px; border-radius: 6px;">View Paper</a>
            {zotero_row}
            {alphaxiv_row}
            {github_row}
        </td>
    </tr>
</table>
"""
    venue_row = (
        f'<tr><td style="font-size: 13px; color: #57606a; padding: 4px 0;">{venue_line}</td></tr>'
        if venue_line
        else ""
    )
    return block_template.format(
        title=title,
        rate=rate,
        authors=authors,
        year=year,
        citations=citations,
        venue_row=venue_row,
        summary=summary,
        paper_url=paper_url,
        zotero_row=zotero_btn,
        alphaxiv_row=alphaxiv_btn,
        github_row=github_btn,
    )
