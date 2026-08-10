from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import inspect_pdf


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# Blackout Proof report",
        "",
        f"- Source: `{report['source']}`",
        f"- SHA-256: `{report['sourceSha256']}`",
        f"- Pages: {report['pageCount']}",
        f"- Verdict: **{report['verdict']}**",
        "",
        "| Severity | Code | Page | Count | Finding |",
        "|---|---|---:|---:|---|",
    ]
    findings = report["findings"]
    assert isinstance(findings, list)
    if not findings:
        lines.append("| info | BP000 | - | 0 | No structural risks found |")
    for item in findings:
        assert isinstance(item, dict)
        lines.append(
            f"| {item['severity']} | {item['code']} | {item['page'] or '-'} | {item['count']} | {item['message']} |"
        )
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a PDF for residual redaction risks.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-findings", action="store_true")
    args = parser.parse_args(argv)
    if args.pdf.suffix.lower() != ".pdf" or not args.pdf.is_file():
        parser.error("input must be an existing PDF")
    report = inspect_pdf(args.pdf)
    rendered = json.dumps(report, indent=2) if args.format == "json" else _markdown(report)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return int(args.fail_on_findings and bool(report["findingCount"]))
