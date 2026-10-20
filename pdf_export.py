"""Markdown-отчёт → брендированный PDF (цвета из trade-report-pdf)."""
from __future__ import annotations

import datetime as dt
import html
import re

import markdown

_EMOJI = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF️‍]+"
)

CSS = """
@page {
  size: A4; margin: 18mm 15mm 20mm 15mm;
  @bottom-left { content: "DISCLAIMER: For educational/research purposes only. Not financial advice.";
                 font-size: 7pt; color: #718096; font-family: "DejaVu Sans", sans-serif; }
  @bottom-right { content: "Page " counter(page) " / " counter(pages); font-size: 7pt; color: #718096; font-family: "DejaVu Sans", sans-serif; }
}
body { font-family: "DejaVu Sans", sans-serif; font-size: 9.5pt; color: #2d3748; line-height: 1.45; }
.cover { border-bottom: 3px solid #1a365d; padding-bottom: 8px; margin-bottom: 14px; }
.cover .brand { color: #1a365d; font-size: 8pt; letter-spacing: 1.5px; text-transform: uppercase; }
.cover .meta { color: #718096; font-size: 8pt; }
h1 { color: #1a365d; font-size: 18pt; margin: 4px 0; }
h2 { color: #1a365d; font-size: 13pt; border-bottom: 1px solid #e2e8f0; padding-bottom: 3px; margin-top: 18px; }
h3 { color: #1a365d; font-size: 11pt; margin-top: 12px; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8.5pt; page-break-inside: auto; }
th { background: #1a365d; color: #fff; text-align: left; padding: 4px 6px; }
td { border-bottom: 1px solid #e2e8f0; padding: 4px 6px; vertical-align: top; }
tr:nth-child(even) td { background: #f7fafc; }
blockquote { background: #fffff0; border-left: 3px solid #d69e2e; margin: 10px 0; padding: 6px 10px; font-size: 8.5pt; }
code { font-family: "DejaVu Sans Mono", monospace; font-size: 8pt; background: #f7fafc; }
pre { background: #f7fafc; padding: 6px; font-size: 7.5pt; white-space: pre-wrap; }
hr { border: none; border-top: 1px solid #e2e8f0; margin: 12px 0; }
"""


def markdown_to_html(md_text: str, title: str) -> str:
    body = markdown.markdown(_EMOJI.sub("", md_text), extensions=["tables", "fenced_code", "sane_lists"])
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<div class="cover"><div class="brand">AI Trading Analyst</div>
<div class="meta">{html.escape(title)} · generated {now}</div></div>
{body}
</body></html>"""


def markdown_to_pdf(md_text: str, title: str) -> bytes:
    from weasyprint import HTML  # импорт здесь: если системных библиотек нет, остальное приложение работает
    return HTML(string=markdown_to_html(md_text, title)).write_pdf()
