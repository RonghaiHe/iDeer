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
            '<tr><td style="padding:4px 0;">'
            '<a href="{url}" '
            'style="display:inline-block;text-decoration:none;font-size:12px;'
            'font-weight:bold;color:#333;background-color:#f2f2f2;'
            'padding:6px 10px;border-radius:4px;">'
            '\U0001f4da Save to Zotero</a>'
            '</td></tr>'.format(url=zotero_save_url)
        )
    github_btn = ""
    if github_issue_url:
        github_btn = (
            '<tr><td style="padding:4px 0;">'
            '<a href="{url}" '
            'style="display:inline-block;text-decoration:none;font-size:12px;'
            'font-weight:bold;color:#fff;background-color:#000000;'
            'padding:6px 10px;border-radius:4px;">'
            '\U0001f4da Add to Online Paper Reader</a>'
            '</td></tr>'.format(url=github_issue_url)
        )
    block_template = """
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
                      font-weight: bold; color: #fff; background-color: #b31b1b;
                      padding: 8px 16px; border-radius: 6px;">PDF</a>
            <a href="https://www.alphaxiv.org/abs/{arxiv_id}"
               style="display: inline-block; text-decoration: none; font-size: 14px;
                      font-weight: bold; color: #fff; background-color: #b13938;
                      padding: 8px 16px; border-radius: 6px; margin-left: 8px;">AlphaXiv</a>
        </td>
    </tr>
    {zotero_row}
    {github_row}
</table>
"""
    return block_template.format(
        title=title,
        rate=rate,
        arxiv_id=arxiv_id,
        summary=summary,
        pdf_url=pdf_url,
        zotero_row=zotero_btn,
        github_row=github_btn,
    )
