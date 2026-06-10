def get_paper_block_html(
    title: str,
    rate: str,
    authors: str,
    venue: str,
    year: str,
    citations: int,
    summary: str,
    paper_url: str,
    zotero_save_url: str = "",
) -> str:
    venue_line = f"<strong>Venue:</strong> {venue}" if venue else ""
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
        </td>
    </tr>
    {zotero_row}
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
    )
