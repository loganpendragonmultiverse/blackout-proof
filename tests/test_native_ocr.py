import json
import os
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from blackout_proof.cli import _markdown
from blackout_proof.core import inspect_pdf
from blackout_proof.review import render_html


@pytest.mark.skipif(
    os.environ.get("BLACKOUT_NATIVE_OCR") != "1", reason="explicit native Tesseract acceptance"
)
def test_real_tesseract_counts_and_unavailable_data(tmp_path):
    # Uses actual PyMuPDF/Tesseract; this is deliberately separate from adapter stubs.
    namespace = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "make_sample.py"))
    source = tmp_path / "raster.pdf"
    namespace["create_sample"](source, raster=True)
    original = source.read_bytes()
    report = inspect_pdf(source, ocr=True)
    review = report["pagePreviews"][0]["ocr_review"]
    assert review == {"status": "completed", "word_count": 2}
    for rendered in [json.dumps(report), _markdown(report), render_html(report)]:
        assert "EXAMPLE REVIEW" not in rendered
    empty = tmp_path / "no-language-data"
    empty.mkdir()
    environment = dict(os.environ, TESSDATA_PREFIX=str(empty), PYTHONNOUSERSITE="1")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "blackout_proof",
            str(source),
            "--ocr",
            "--format",
            "json",
            "--fail-on-findings",
        ],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2, result.stderr
    incomplete = json.loads(result.stdout)
    assert incomplete["verdict"] == "incomplete" and not incomplete["inspectionComplete"]
    assert incomplete["pagePreviews"][0]["ocr_review"]["status"] == "unavailable"
    assert "word_count" not in incomplete["pagePreviews"][0]["ocr_review"]
    assert "EXAMPLE REVIEW" not in result.stdout + result.stderr
    assert source.read_bytes() == original
