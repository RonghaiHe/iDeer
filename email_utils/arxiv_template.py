import base64
from pathlib import Path

_brand_dir = Path(__file__).resolve().parent.parent / "docs" / "brand"

with open(_brand_dir / "arxiv.svg", "rb") as f:
    _arxiv_logo_src = "data:image/svg+xml;base64," + base64.b64encode(f.read()).decode()

with open(_brand_dir / "alphaxiv.png", "rb") as f:
    _alphaxiv_logo_src = "data:image/png;base64," + base64.b64encode(f.read()).decode()

with open(_brand_dir / "zotero.png", "rb") as f:
    _zotero_logo_src = "data:image/png;base64," + base64.b64encode(f.read()).decode()

_icon_style = "height:14px;vertical-align:middle;margin-right:4px;"
_icon_style_zotero = "height:14px;vertical-align:middle;margin-right:4px;"


def get_paper_block_html(
    title: str,
    rate: str,
    arxiv_id: str,
    summary: str,
    pdf_url: str,
    zotero_save_url: str = "",
    github_issue_url: str = "",
) -> str:
    zotero_btn = ""
    if zotero_save_url:
        zotero_btn = (
            f'<a href="{zotero_save_url}" '
            f'style="display:inline-block;text-decoration:none;font-size:14px;'
            f'font-weight:bold;color:#fff;background-color:#E0E0E0;'
            f'padding:8px 16px;border-radius:6px;margin-left:8px;">'
            f'<img src="{_zotero_logo_src}" style="{_icon_style_zotero}" alt="">Save to Zotero</a>'
        )
    github_btn = ""
    if github_issue_url:
        github_btn = (
            '<a href="{url}" '
            'style="display:inline-block;text-decoration:none;font-size:14px;'
            'font-weight:bold;color:#fff;background-color:#E0E0E0;'
            'padding:8px 16px;border-radius:6px;margin-left:8px;">'
            '\U0001f4da Add to Online Paper Reader</a>'.format(url=github_issue_url)
        )
    return f"""
    <table border="0" cellpadding="0" cellspacing="0" width="100%"
           style="font-family: Arial, sans-serif; border: 1px solid #ddd; border-radius: 8px;
                  padding: 16px; background-color: #f9f9f9;">
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
        <td style="font-size: 14px; color: #57606a; padding: 8px 0;">
            <strong>arXiv ID:</strong> {arxiv_id}
        </td>
    </tr>
    <tr>
        <td style="font-size: 14px; color: #333; padding: 8px 0;">
            <strong>TLDR:</strong> {summary}
        </td>
    </tr>
    <tr>
        <td style="padding: 8px 0;">
            <a href="{pdf_url}"
               style="display: inline-block; text-decoration: none; font-size: 14px;
                      font-weight: bold; color: #fff; background-color: #E0E0E0;
                      padding: 8px 16px; border-radius: 6px;">
               <img src="{_arxiv_logo_src}" style="{_icon_style}" alt="">PDF</a>
            <a href="https://www.alphaxiv.org/abs/{arxiv_id}"
               style="display: inline-block; text-decoration: none; font-size: 14px;
                      font-weight: bold; color: #fff; background-color: #E0E0E0;
                      padding: 8px 16px; border-radius: 6px; margin-left: 8px;">
               <img src="{_alphaxiv_logo_src}" style="{_icon_style}" alt="">AlphaXiv</a>
            {zotero_btn}
            {github_btn}
        </td>
    </tr>
</table>
"""
