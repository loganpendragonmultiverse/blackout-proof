from __future__ import annotations

import hashlib
import math
import os
import re
import stat
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pymupdf


class InspectionError(ValueError):
    """No complete inspection is available; messages contain no PDF values."""


@dataclass(frozen=True)
class InspectionLimits:
    max_file_bytes: int = 32 * 1024 * 1024
    max_pages: int = 1000
    max_xrefs: int = 100_000
    max_object_chars: int = 8 * 1024 * 1024
    max_page_items: int = 100_000
    max_geometry_checks: int = 1_000_000
    max_ocr_pixels: int = 20_000_000
    max_total_ocr_pixels: int = 100_000_000

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")


def _within(count: int, maximum: int, label: str) -> None:
    if count > maximum:
        raise InspectionError(f"Inspection limit exceeded: {label}; no complete result")


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    page: int | None
    count: int
    message: str


def _dark_fill(drawing: dict[str, Any]) -> bool:
    fill = drawing.get("fill")
    opacity = float(drawing.get("fill_opacity", 1.0) or 0.0)
    return (
        isinstance(fill, (list, tuple))
        and bool(fill)
        and max(float(value) for value in fill) <= 0.15
        and opacity >= 0.8
    )


def _pdf_names(value: str) -> Iterator[str]:
    """Read PDF name tokens, omitting comments, literal strings and hex strings."""
    index = 0
    delimiters = "()<>[]{}/%\x00\t\n\f\r "
    while index < len(value):
        char = value[index]
        if char == "%":
            newline = value.find("\n", index)
            index = len(value) if newline < 0 else newline + 1
        elif char == "(":
            depth = 1
            index += 1
            while index < len(value) and depth:
                if value[index] == "\\":
                    index += 2
                    continue
                depth += int(value[index] == "(") - int(value[index] == ")")
                index += 1
        elif char == "<" and value[index : index + 2] != "<<":
            closing = value.find(">", index + 1)
            index = len(value) if closing < 0 else closing + 1
        elif char == "/":
            start = index = index + 1
            while index < len(value) and value[index] not in delimiters:
                index += 1
            yield re.sub(
                r"#([0-9a-fA-F]{2})", lambda match: chr(int(match[1], 16)), value[start:index]
            )
        else:
            index += 2 if value[index : index + 2] == "<<" else 1


def _covered_glyph_count(
    page: Any, drawings: list[dict[str, Any]], limits: InspectionLimits
) -> int:
    covers = [item for item in drawings if _dark_fill(item) and item.get("rect")]
    if not covers:
        return 0
    spans = page.get_texttrace()
    _within(len(spans), limits.max_page_items, "page text spans")
    checks = count = glyphs = 0
    for span in spans:
        glyphs += len(span["chars"])
        _within(glyphs, limits.max_page_items, "page traced glyphs")
        for character in span["chars"]:
            if chr(character[0]).isspace():
                continue
            glyph_rect = pymupdf.Rect(character[3])  # type: ignore[no-untyped-call]
            for cover in covers:
                checks += 1
                _within(checks, limits.max_geometry_checks, "page geometry comparisons")
                # Both seqno values belong to these specific paint operations;
                # never borrow an earlier span's order for a later foreground word.
                if cover["seqno"] > span["seqno"] and not (glyph_rect & cover["rect"]).is_empty:
                    count += 1
                    break
    return count


def _analyse_pdf(raw: bytes, ocr: bool, limits: InspectionLimits) -> dict[str, object]:
    findings: list[Finding] = []
    previews: list[dict[str, Any]] = []
    with pymupdf.open(stream=raw, filetype="pdf") as document:  # type: ignore[no-untyped-call]
        if document.needs_pass:
            raise InspectionError("Encrypted PDF requires prior authorized local decryption")
        if document.page_count < 1:
            raise InspectionError("PDF contains no pages; no complete result")
        _within(document.page_count, limits.max_pages, "pages")
        xrefs = document.xref_length() - 1
        _within(xrefs, limits.max_xrefs, "xref objects")
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
        javascript = layers = object_chars = 0
        for xref in range(1, xrefs + 1):
            obj = document.xref_object(xref, compressed=True)
            object_chars += len(obj)
            _within(object_chars, limits.max_object_chars, "combined serialized object characters")
            names = set(_pdf_names(obj))
            javascript += int(bool(names & {"JavaScript", "JS"}))
            layers += int(bool(names & {"OCG", "OCProperties"}))
        if javascript:
            findings.append(
                Finding(
                    "high",
                    "BP004",
                    None,
                    javascript,
                    "JavaScript-related PDF names remain in object structure.",
                )
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
        ocr_complete = True
        total_ocr_pixels = 0
        for page_number, page in enumerate(document, start=1):
            annotations = []
            for annotation in page.annots() or []:
                annotations.append(annotation)
                _within(len(annotations), limits.max_page_items, "page annotations")
            pending_redactions = sum(annotation.type[1] == "Redact" for annotation in annotations)
            if pending_redactions:
                findings.append(
                    Finding(
                        "warning",
                        "BP008",
                        page_number,
                        pending_redactions,
                        "Unapplied Redact annotations remain on this page. A marker is unfinished redaction, not proof of secret text.",
                    )
                )
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
            drawings = page.get_drawings()
            _within(len(drawings), limits.max_page_items, "page drawings")
            covers = [item["rect"] for item in drawings if _dark_fill(item) and item.get("rect")]
            regions = []
            for cover in covers:
                rect = cover * page.rotation_matrix
                regions.append([round(float(value), 3) for value in rect])
            width, height = float(page.rect.width), float(page.rect.height)
            if not all(math.isfinite(value) and value > 0 for value in (width, height)):
                raise InspectionError("Invalid page dimensions; no complete result")
            ocr_review: dict[str, object] = {"status": "not-requested"}
            if ocr:
                pixels = math.ceil(width * 150 / 72) * math.ceil(height * 150 / 72)
                _within(pixels, limits.max_ocr_pixels, "OCR raster pixels per page")
                total_ocr_pixels += pixels
                _within(total_ocr_pixels, limits.max_total_ocr_pixels, "combined OCR raster pixels")
                try:
                    textpage = page.get_textpage_ocr(full=True, dpi=150)
                    words = page.get_text("words", textpage=textpage)
                    _within(len(words), limits.max_page_items, "OCR words per page")
                    ocr_review = {"status": "completed", "word_count": len(words)}
                except InspectionError:
                    raise
                except Exception as exc:
                    # PyMuPDF raises plain Exception for missing language data.
                    # Preserve unexpected programming/resource exceptions.
                    if type(exc) is not Exception and not isinstance(
                        exc, (RuntimeError, ValueError, OSError, pymupdf.mupdf.FzErrorBase)
                    ):
                        raise
                    ocr_complete = False
                    ocr_review = {
                        "status": "unavailable",
                        "reason": "Local OCR failed or language data unavailable; review is incomplete",
                    }
            previews.append(
                {
                    "page": page_number,
                    "width": width,
                    "height": height,
                    "dark_regions": regions,
                    "ocr_review": ocr_review,
                }
            )
            covered_glyphs = _covered_glyph_count(page, drawings, limits)
            if covered_glyphs:
                findings.append(
                    Finding(
                        "critical",
                        "BP007",
                        page_number,
                        covered_glyphs,
                        "Extractable glyph instances intersect a later dark opaque cover.",
                    )
                )
        return {
            "schemaVersion": 1,
            "pagePreviews": previews,
            "previewMode": "geometry-only; source text and images are omitted",
            "ocrNote": "Optional local OCR counts are review aids, not sanitization proof",
            "ocrRequested": ocr,
            "inspectionComplete": ocr_complete,
            "limits": asdict(limits),
            "pageCount": document.page_count,
            "findingCount": len(findings),
            "findings": [asdict(item) for item in findings],
            "verdict": "incomplete"
            if not ocr_complete
            else "review"
            if findings
            else "no-structural-risks-found",
        }


def _identity(info: os.stat_result) -> tuple[int, ...]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def inspect_pdf(
    path: Path, *, ocr: bool = False, limits: InspectionLimits | None = None
) -> dict[str, object]:
    if type(ocr) is not bool:
        raise ValueError("ocr must be a boolean")
    if limits is not None and not isinstance(limits, InspectionLimits):
        raise ValueError("limits must be InspectionLimits")
    selected = limits or InspectionLimits()
    with path.open("rb") as stream:
        original = os.fstat(stream.fileno())
        if not stat.S_ISREG(original.st_mode):
            raise InspectionError("Input must be a regular PDF file")
        _within(original.st_size, selected.max_file_bytes, "file bytes")
        raw = stream.read(min(selected.max_file_bytes, original.st_size) + 1)
        _within(len(raw), selected.max_file_bytes, "file bytes")
        digest = hashlib.sha256(raw).hexdigest()
        try:
            result = _analyse_pdf(raw, ocr, selected)
        except InspectionError:
            raise
        except (
            RuntimeError,
            ValueError,
            TypeError,
            OverflowError,
            pymupdf.mupdf.FzErrorBase,
        ) as exc:
            raise InspectionError("PDF could not be inspected; no complete result") from exc
        stream.seek(0)
        check = hashlib.sha256()
        read = 0
        while block := stream.read(min(1024 * 1024, selected.max_file_bytes + 1 - read)):
            read += len(block)
            _within(read, selected.max_file_bytes, "source verification bytes")
            check.update(block)
        field_names = ("device", "inode", "size", "mtime_ns", "ctime_ns")
        differences: list[str] = []
        for label, current in (("descriptor", os.fstat(stream.fileno())), ("path", path.stat())):
            differences.extend(
                label + ":" + name
                for name, before, after in zip(
                    field_names, _identity(original), _identity(current), strict=True
                )
                if before != after
            )
        if check.hexdigest() != digest:
            differences.append("content-hash")
        if differences:
            raise InspectionError(
                "Source changed during inspection ("
                + ", ".join(differences)
                + "); no complete result"
            )
        return {**result, "source": path.name, "sourceSha256": digest}
