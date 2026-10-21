import json
from dataclasses import fields
from pathlib import Path

import pymupdf
import pytest

from blackout_proof import core
from blackout_proof.cli import _markdown, main
from blackout_proof.core import InspectionError, InspectionLimits, _pdf_names, inspect_pdf
from blackout_proof.review import render_html


def sample(path, *, pages=1, background=False, covered=False, literals=False):
    with pymupdf.open() as document:
        for _ in range(pages):
            page = document.new_page(width=600, height=200)
            area = pymupdf.Rect(20, 20, 550, 160)
            if background:
                page.draw_rect(area, fill=(0, 0, 0))
            page.insert_text(
                (40, 100),
                "SYNTHETIC CANARY",
                fontsize=32,
                color=(1, 1, 1) if background else (0, 0, 0),
            )
            if covered:
                page.draw_rect(area, fill=(0, 0, 0))
        document.set_metadata(
            {"title": "Literal /JS /JavaScript /OCG /OCProperties"} if literals else {}
        )
        document.save(path)


def test_paint_order_and_literal_names(tmp_path):
    for mode in ["background", "covered", "literals"]:
        path = tmp_path / (mode + ".pdf")
        sample(path, **{mode: True})
        before = path.read_bytes()
        report = inspect_pdf(path)
        codes = {finding["code"] for finding in report["findings"]}
        assert ("BP007" in codes) == (mode == "covered")
        assert "BP004" not in codes and "BP005" not in codes
        assert "SYNTHETIC CANARY" not in json.dumps(report) + _markdown(report) + render_html(
            report
        )
        assert path.read_bytes() == before


@pytest.mark.parametrize(
    "source,names",
    [
        ("<< /J#53 (SYNTHETIC /JS) /S /JavaScript /OCG null >>", {"JS", "S", "JavaScript", "OCG"}),
        ("% /JS\n /OCProperties (nested ( /JS ) \\) end) <2f4a53>", {"OCProperties"}),
        ("% /JS", set()),
        ("(unclosed /JS", set()),
        ("<2f4a53", set()),
        ("/JSON /JSuffix /Object", {"JSON", "JSuffix", "Object"}),
    ],
)
def test_pdf_name_lexer(source, names):
    assert set(_pdf_names(source)) == names


@pytest.mark.parametrize("field", [field.name for field in fields(InspectionLimits)])
@pytest.mark.parametrize("value", [0, -1, True, 1.5, None, "1"])
def test_limits_are_positive_integers(field, value):
    with pytest.raises(ValueError, match="positive integer"):
        InspectionLimits(**{field: value})


@pytest.mark.parametrize("value", [1, "yes", [], None])
def test_ocr_api_is_boolean(tmp_path, value):
    with pytest.raises(ValueError, match="boolean"):
        inspect_pdf(tmp_path / "absent.pdf", ocr=value)


def test_limits_api_requires_limit_object(tmp_path):
    with pytest.raises(ValueError, match="InspectionLimits"):
        inspect_pdf(tmp_path / "absent.pdf", limits={})


@pytest.mark.parametrize(
    "budget",
    [
        "max_file_bytes",
        "max_pages",
        "max_xrefs",
        "max_object_chars",
        "max_page_items",
        "max_geometry_checks",
        "max_ocr_pixels",
        "max_total_ocr_pixels",
    ],
)
def test_budget_exhaustion_never_claims_success(tmp_path, budget, monkeypatch):
    path = tmp_path / "sample.pdf"
    sample(path, pages=2, covered=True)
    with pytest.raises(InspectionError, match="limit exceeded"):
        inspect_pdf(path, ocr="ocr_pixels" in budget, limits=InspectionLimits(**{budget: 1}))
    with pytest.raises(SystemExit) as error:
        main(
            [str(path), "--" + budget.replace("_", "-"), "1"]
            + (["--ocr"] if "ocr_pixels" in budget else [])
        )
    assert error.value.code == 2


def test_ocr_raster_budget_checked_before_native_call(tmp_path, monkeypatch):
    path = tmp_path / "sample.pdf"
    sample(path)

    def forbidden(*args, **kwargs):
        raise AssertionError("OCR must not rasterize")

    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", forbidden)
    with pytest.raises(InspectionError, match="OCR raster"):
        inspect_pdf(path, ocr=True, limits=InspectionLimits(max_ocr_pixels=1))


def test_ocr_unavailable_is_incomplete_and_value_free(tmp_path, monkeypatch):
    path = tmp_path / "sample.pdf"
    sample(path)

    def unavailable(*args, **kwargs):
        raise RuntimeError("SYNTHETIC ENGINE SECRET")

    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", unavailable)
    report = inspect_pdf(path, ocr=True)
    assert report["verdict"] == "incomplete" and not report["inspectionComplete"]
    assert report["pagePreviews"][0]["ocr_review"]["status"] == "unavailable"
    assert "word_count" not in report["pagePreviews"][0]["ocr_review"]
    assert main([str(path), "--ocr", "--fail-on-findings"]) == 2
    assert "SYNTHETIC ENGINE SECRET" not in json.dumps(report) + _markdown(report) + render_html(
        report
    )


def test_ocr_word_budget_is_not_engine_unavailability(tmp_path, monkeypatch):
    path = tmp_path / "sample.pdf"
    sample(path)
    monkeypatch.setattr(
        pymupdf.Page, "get_textpage_ocr", lambda self, **kwargs: self.get_textpage()
    )
    with pytest.raises(InspectionError, match="OCR words"):
        inspect_pdf(path, ocr=True, limits=InspectionLimits(max_page_items=1))


@pytest.mark.parametrize("change", ["rewrite", "replace", "grow"])
def test_changed_source_refuses_report(tmp_path, monkeypatch, change):
    path = tmp_path / "sample.pdf"
    sample(path)
    before = path.read_bytes()
    original = core._analyse_pdf
    blocked = []

    def changing(*args, **kwargs):
        result = original(*args, **kwargs)
        if change == "replace":
            other = tmp_path / "replacement.pdf"
            other.write_bytes(before)
            try:
                other.replace(path)
            except PermissionError:
                # Windows may protect an open source handle from replacement.
                blocked.append(True)
        else:
            path.write_bytes(before + b"\n" if change == "grow" else before[:-1])
        return result

    monkeypatch.setattr(core, "_analyse_pdf", changing)
    try:
        result = inspect_pdf(path, limits=InspectionLimits(max_file_bytes=len(before)))
    except InspectionError as exc:
        assert not blocked
        assert "changed" in str(exc) or "verification bytes" in str(exc)
    else:
        assert change == "replace" and blocked
        assert path.read_bytes() == before
        assert result["inspectionComplete"]


def test_regular_input_required(tmp_path, monkeypatch):
    path = tmp_path / "sample.pdf"
    sample(path)
    monkeypatch.setattr(core.stat, "S_ISREG", lambda mode: False)
    with pytest.raises(InspectionError, match="regular"):
        inspect_pdf(path)


def test_invalid_dimensions_and_no_pages(tmp_path, monkeypatch):
    path = tmp_path / "sample.pdf"
    sample(path)
    monkeypatch.setattr(pymupdf.Page, "rect", property(lambda self: pymupdf.Rect(0, 0, 0, 0)))
    with pytest.raises(InspectionError, match="dimensions"):
        inspect_pdf(path)

    class Empty:
        needs_pass = False
        page_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(core.pymupdf, "open", lambda **kwargs: Empty())
    with pytest.raises(InspectionError, match="no pages"):
        inspect_pdf(path)


def test_reports_summary_and_literal_source_name(tmp_path):
    path = tmp_path / "safe.pdf"
    sample(path, literals=True)
    report = inspect_pdf(path)
    report["source"] = "<img src=x onerror=x>`\n# FORGED|"
    html = render_html(report)
    markdown = _markdown(report)
    assert report["sourceSha256"] in html and report["sourceSha256"] in markdown
    assert html.count("BP001") == 1
    assert "<img src=x" not in html and "<img src=x" not in markdown
    assert "\n# FORGED" not in markdown
    report["pagePreviews"] = []
    report["pageCount"] = 0
    assert "BP001" in render_html(report) and "Pages: 0" in render_html(report)


def test_exclusive_outputs_aliases_and_io_errors(tmp_path, monkeypatch):
    path = tmp_path / "sample.pdf"
    sample(path)
    before = path.read_bytes()
    target = tmp_path / "report.json"
    assert main([str(path), "--format", "json", "--output", str(target)]) == 0
    content = target.read_bytes()
    for output in [path, target, tmp_path / "missing" / "report.md"]:
        with pytest.raises(SystemExit) as error:
            main([str(path), "--output", str(output)])
        assert error.value.code == 2
    assert target.read_bytes() == content and path.read_bytes() == before
    raced = tmp_path / "raced"
    original = Path.open

    def racing(self, mode="r", *args, **kwargs):
        if self == raced and mode == "x":
            with original(self, "w") as stream:
                stream.write("retain concurrent file")
        return original(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", racing)
    with pytest.raises(SystemExit):
        main([str(path), "--output", str(raced)])
    assert raced.read_text() == "retain concurrent file"
    link = tmp_path / "dangling"
    try:
        link.symlink_to(tmp_path / "missing-target")
    except OSError:
        return
    with pytest.raises(SystemExit):
        main([str(path), "--output", str(link)])
    assert not (tmp_path / "missing-target").exists()


@pytest.mark.parametrize("value", ["0", "-1", "1.5", "bad"])
def test_cli_invalid_limit(tmp_path, value):
    with pytest.raises(SystemExit) as error:
        main([str(tmp_path / "sample.pdf"), "--max-pages", value])
    assert error.value.code == 2


def test_foreground_overlap_has_its_own_paint_provenance(tmp_path):
    path = tmp_path / "overlap.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        point = (72, 72)
        page.insert_text(point, "SECRET", fontsize=20)
        page.draw_rect(pymupdf.Rect(60, 40, 250, 90), fill=(0, 0, 0))
        page.insert_text(point, "PUBLIC", fontsize=20, color=(1, 1, 1))
        document.save(path)
    finding = next(item for item in inspect_pdf(path)["findings"] if item["code"] == "BP007")
    assert finding["count"] == 6
    assert "glyph instances" in finding["message"]


def test_cover_in_text_span_whitespace_is_not_a_glyph(tmp_path):
    path = tmp_path / "gap.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "A          B", fontsize=20)
        page.draw_rect(pymupdf.Rect(100, 45, 110, 80), fill=(0, 0, 0))
        document.save(path)
    assert "BP007" not in {item["code"] for item in inspect_pdf(path)["findings"]}


def test_huge_valid_budget_does_not_overflow_native_read_size(tmp_path):
    source = tmp_path / "sample.pdf"
    sample(source)
    assert inspect_pdf(source, limits=InspectionLimits(max_file_bytes=10**100))[
        "inspectionComplete"
    ]
