import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from blackout_proof.cli import main
from blackout_proof.core import inspect_pdf
from blackout_proof.review import render_html


def make_pdf(
    path: Path,
    *,
    rotate: bool = False,
    transparent: bool = False,
    applied: bool = False,
    layer: bool = False,
) -> None:
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((200, 300), "SOURCE-TEXT-CANARY", rotate=90 if rotate else 0)
        rect = page.search_for("SOURCE-TEXT-CANARY")[0]
        if applied:
            page.add_redact_annot(rect, fill=(0, 0, 0))
            page.apply_redactions()
        else:
            page.draw_rect(rect, fill=(0, 0, 0), fill_opacity=0.3 if transparent else 1)
        if layer:
            oc = doc.add_ocg("PRIVATE-LAYER-CANARY")
            page.insert_text((72, 200), "HIDDEN-LAYER-CANARY", oc=oc)
        if rotate:
            page.set_rotation(90)
        doc.save(path)


@pytest.mark.parametrize("mode", ["normal", "rotate", "transparent", "applied", "layer"])
def test_real_pdf_review_cases(tmp_path: Path, mode: str) -> None:
    source = tmp_path / "sample.pdf"
    make_pdf(source, **({mode: True} if mode != "normal" else {}))
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    report = inspect_pdf(source)
    codes = {item["code"] for item in report["findings"]}
    assert ("BP007" in codes) == (mode not in {"transparent", "applied"})
    if mode == "layer":
        assert "BP005" in codes
    for output in (json.dumps(report), render_html(report)):
        assert "SOURCE-TEXT-CANARY" not in output
        assert "PRIVATE-LAYER-CANARY" not in output
        assert "HIDDEN-LAYER-CANARY" not in output
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    output = tmp_path / "review.html"
    assert main([str(source), "--format", "html", "--output", str(output)]) == 0
    assert "Geometry-only" in output.read_text()
    with pytest.raises(SystemExit):
        main([str(source), "--output", str(output)])


def test_encrypted_and_damaged_are_actionable(tmp_path: Path) -> None:
    encrypted = tmp_path / "encrypted.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.save(
            encrypted, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="fixture"
        )
    with pytest.raises(ValueError, match="Encrypted"):
        inspect_pdf(encrypted)
    damaged = tmp_path / "damaged.pdf"
    damaged.write_bytes(b"%PDF broken")
    with pytest.raises(SystemExit) as error:
        main([str(damaged)])
    assert error.value.code == 2


def test_opt_in_ocr_success_and_missing_engine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "sample.pdf"
    make_pdf(source)
    monkeypatch.setattr(
        pymupdf.Page, "get_textpage_ocr", lambda self, **kwargs: self.get_textpage()
    )
    report = inspect_pdf(source, ocr=True)
    assert report["pagePreviews"][0]["ocr_review"]["status"] == "completed"
    assert "Word count:" in render_html(report)

    def missing(self, **kwargs):
        raise RuntimeError("Tesseract unavailable")

    monkeypatch.setattr(pymupdf.Page, "get_textpage_ocr", missing)
    assert inspect_pdf(source, ocr=True)["pagePreviews"][0]["ocr_review"]["status"] == "unavailable"
