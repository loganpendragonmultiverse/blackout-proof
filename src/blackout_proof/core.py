from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pymupdf


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    page: int | None
    count: int
    message: str


def _dark_fill(drawing: dict[str, Any]) -> bool:
    fill = drawing.get("fill")
    opacity = float(drawing.get("fill_opacity", 1.0))
    return (
        isinstance(fill, (list, tuple))
        and bool(fill)
        and max(float(value) for value in fill) <= 0.15
        and opacity >= 0.8
    )


def _covered_word_count(page: Any) -> int:
    covers = [item["rect"] for item in page.get_drawings() if _dark_fill(item) and item.get("rect")]
    count = 0
    for word in page.get_text("words"):
        word_rect = pymupdf.Rect(word[:4])  # type: ignore[no-untyped-call]
        if any(not (word_rect & cover).is_empty for cover in covers):
            count += 1
    return count


def inspect_pdf(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    findings: list[Finding] = []
    with pymupdf.open(stream=raw, filetype="pdf") as document:  # type: ignore[no-untyped-call]
        metadata_count = sum(bool(value) for value in document.metadata.values())
        if metadata_count:
            findings.append(
                Finding(
                    "medium",
                    "BP001",
                    None,
                    metadata_count,
                    "Document metadata fields remain populated.",
                )
            )
        attachments = len(document.embfile_names())
        if attachments:
            findings.append(
                Finding("high", "BP002", None, attachments, "Embedded files remain in the PDF.")
            )
        if bool(document.is_form_pdf):
            findings.append(
                Finding("medium", "BP003", None, 1, "Interactive form content remains in the PDF.")
            )

        javascript = 0
        layers = 0
        for xref in range(1, document.xref_length()):
            obj = document.xref_object(xref, compressed=True)
            javascript += int("/JavaScript" in obj or "/JS" in obj)
            layers += int("/OCG" in obj or "/OCProperties" in obj)
        if javascript:
            findings.append(
                Finding("high", "BP004", None, javascript, "JavaScript actions remain in the PDF.")
            )
        if layers:
            findings.append(
                Finding(
                    "medium",
                    "BP005",
                    None,
                    layers,
                    "Optional-content layer objects remain in the PDF.",
                )
            )

        for page_number, page in enumerate(document, start=1):
            annotations = list(page.annots() or [])
            non_redaction = sum(annotation.type[1] != "Redact" for annotation in annotations)
            if non_redaction:
                findings.append(
                    Finding(
                        "medium",
                        "BP006",
                        page_number,
                        non_redaction,
                        "Non-redaction annotations remain on this page.",
                    )
                )
            covered_words = _covered_word_count(page)
            if covered_words:
                findings.append(
                    Finding(
                        "critical",
                        "BP007",
                        page_number,
                        covered_words,
                        "Extractable text intersects a dark opaque cover.",
                    )
                )

        return {
            "schemaVersion": 1,
            "source": path.name,
            "sourceSha256": hashlib.sha256(raw).hexdigest(),
            "pageCount": document.page_count,
            "findingCount": len(findings),
            "findings": [asdict(item) for item in findings],
            "verdict": "review" if findings else "no-structural-risks-found",
        }
