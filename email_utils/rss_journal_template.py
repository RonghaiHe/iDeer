import base64
from pathlib import Path

_brand_dir = Path(__file__).resolve().parent.parent / "docs" / "brand"

with open(_brand_dir / "zotero.png", "rb") as f:
    _zotero_logo_src = "data:image/png;base64," + base64.b64encode(f.read()).decode()

_icon_style_zotero = "height:14px;vertical-align:middle;margin-right:4px;"

_THEME_COLOR = "#059669"
_THEME_RGB = "5,150,105"


def get_journal_paper_block_html(
    title: str,
    rate: str,
    journal_name: str,
    journal_full_name: str,
    published_at: str,
    summary: str,
    paper_url: str,
    zotero_save_url: str = "",
) -> str:
    journal_label = f"{journal_name} ({journal_full_name})" if journal_full_name and journal_full_name != journal_name else journal_name
    zotero_btn = ""
    if zotero_save_url:
        zotero_btn = (
            f'<a href="{zotero_save_url}" '
            f'style="display:inline-block;text-decoration:none;font-size:14px;'
            f'font-weight:bold;color:#fff;background-color:#6c3ec1;'
            f'padding:8px 16px;border-radius:6px;margin-left:8px;">'
            f'<img src="{_zotero_logo_src}" style="{_icon_style_zotero}" alt="">Save to Zotero</a>'
        )
    block_template = """
    <table border="0" cellpadding="0" cellspacing="0" width="100%%"
           style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px;
                  padding: 16px; background-color: #f0fdf4;">
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
        <td style="padding: 4px 0;">
            <span style="display:inline-block;padding:3px 10px;border-radius:999px;background:rgba({_theme_rgb},0.1);
                         color:{_theme_color};font-size:12px;font-weight:600;">
                {journal_label}
            </span>
            {published_at_html}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {summary}
        </td>
    </tr>
    <tr>
        <td style="padding: 8px 0;">
            <a href="{paper_url}"
               style="display: inline-block; text-decoration: none; font-size: 14px;
                      font-weight: bold; color: #fff; background-color: {_theme_color};
                      padding: 8px 16px; border-radius: 6px;">View Paper</a>
            {zotero_row}
        </td>
    </tr>
</table>
"""
    published_at_html = (
        f' <span style="font-size:12px;color:#6b7280;margin-left:8px;">{published_at}</span>'
        if published_at
        else ""
    )
    return block_template.format(
        title=title,
        rate=rate,
        journal_label=journal_label,
        published_at_html=published_at_html,
        summary=summary,
        paper_url=paper_url,
        zotero_row=zotero_btn,
        _theme_color=_THEME_COLOR,
        _theme_rgb=_THEME_RGB,
    )
