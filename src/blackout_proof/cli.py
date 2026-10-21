from __future__ import annotations

import argparse
import json
import re
from dataclasses import fields
from html import escape
from pathlib import Path

from .core import InspectionLimits, inspect_pdf
from .review import render_html


def _literal(value: object) -> str:
    text = escape(" ".join(str(value).splitlines()), quote=False)
    return re.sub(r"([\\`*_{}\[\]()#+.!|~>-])", r"\\\1", text)


def _markdown(report: dict[str, object]) -> str:
    lines = [
        "# Blackout Proof report",
        "",
        f"- Source: {_literal(report['source'])}",
        f"- SHA-256: `{report['sourceSha256']}`",
        f"- Pages: {report['pageCount']}",
        f"- Complete: {report['inspectionComplete']}",
        f"- OCR requested: {report['ocrRequested']}",
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
    previews = report["pagePreviews"]
    assert isinstance(previews, list)
    lines.extend(["", "## OCR review", ""])
    for page in previews:
        review = page["ocr_review"]
        detail = f"; word count: {review['word_count']}" if "word_count" in review else ""
        lines.append(f"- Page {page['page']}: {review['status']}{detail}")
    return "\n".join(lines)


def _positive(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("limit must be a positive integer")
    return number


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a PDF for residual redaction risks.")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--format", choices=("json", "markdown", "html"), default="markdown")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fail-on-findings", action="store_true")
    parser.add_argument(
        "--ocr",
        action="store_true",
        help="Opt-in local OCR word-count review (requires Tesseract data)",
    )
    for field in fields(InspectionLimits):
        parser.add_argument(
            "--" + field.name.replace("_", "-"),
            type=_positive,
            default=field.default,
            help=f"Inspection budget (default {field.default}); exhaustion gives no complete result",
        )
    args = parser.parse_args(argv)
    try:
        if args.pdf.suffix.lower() != ".pdf" or not args.pdf.is_file():
            parser.error("input must be an existing PDF")
        if args.output and (
            args.output.is_symlink() or args.output.resolve() == args.pdf.resolve()
        ):
            parser.error("output must be a new file distinct from the source")
        limits = InspectionLimits(
            **{field.name: getattr(args, field.name) for field in fields(InspectionLimits)}
        )
        report = inspect_pdf(args.pdf, ocr=args.ocr, limits=limits)
        rendered = (
            json.dumps(report, indent=2)
            if args.format == "json"
            else render_html(report)
            if args.format == "html"
            else _markdown(report)
        )
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(rendered + "\n")
        else:
            print(rendered)
    except OSError:
        parser.error(
            "Input or report output could not be accessed; output must be a new writable file"
        )
    except (RuntimeError, ValueError, TypeError) as exc:
        parser.error(str(exc))
    if not report["inspectionComplete"]:
        return 2
    return int(args.fail_on_findings and bool(report["findingCount"]))
