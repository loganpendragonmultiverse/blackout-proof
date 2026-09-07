from __future__ import annotations

from html import escape
from typing import Any


def render_html(report: dict[str, Any]) -> str:
    sections: list[str] = []
    for page in report["pagePreviews"]:
        regions = "".join(
            f'<rect x="{x}" y="{y}" width="{max(0, right - x)}" height="{max(0, bottom - y)}"/>'
            for x, y, right, bottom in page["dark_regions"]
        )
        findings = "".join(
            f"<li><strong>{escape(item['code'])} / {escape(item['severity'])}</strong>: {escape(item['message'])} Count: {item['count']}</li>"
            for item in report["findings"]
            if item["page"] in (None, page["page"])
        )
        ocr = page["ocr_review"]
        sections.append(
            f'<section id="page-{page["page"]}"><h2>Page {page["page"]}</h2><div class="grid"><svg role="img" aria-label="Geometry preview of dark cover regions; source content omitted" viewBox="0 0 {page["width"]} {page["height"]}">{regions}</svg><div><ul>{findings or "<li>No structural findings on this page</li>"}</ul><p>OCR: {escape(str(ocr["status"]))}. {"Word count: " + str(ocr["word_count"]) if "word_count" in ocr else ""}</p></div></div></section>'
        )
    links = " ".join(
        f'<a href="#page-{p["page"]}">Page {p["page"]}</a>' for p in report["pagePreviews"]
    )
    return (
        '<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Blackout Proof review</title><style>body{font:17px system-ui;background:#101820;color:#edf3f5;max-width:1100px;margin:auto;padding:24px;line-height:1.6}a{color:#8ee2ff}nav{display:flex;gap:14px;flex-wrap:wrap}section{margin:30px 0;padding:20px;border:1px solid #547080;border-radius:12px}.grid{display:grid;grid-template-columns:minmax(150px,1fr) 2fr;gap:24px}svg{background:white;width:100%;max-height:480px}rect{fill:#333;stroke:#d33;stroke-width:2}li{margin:12px 0}p{overflow-wrap:anywhere}@media(max-width:600px){.grid{grid-template-columns:1fr}body{padding:14px}}</style><h1>Blackout Proof review</h1><p>Geometry-only page previews show dark cover locations. Source text and images are deliberately omitted. A rectangle is a review region, not proof of a failed redaction. Findings remain heuristic; a clean result does not prove sanitization.</p><nav>'
        + links
        + "</nav>"
        + "".join(sections)
        + "</html>"
    )
