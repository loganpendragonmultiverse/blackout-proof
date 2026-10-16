import hashlib

import pymupdf
import pytest

from blackout_proof.cli import main
from blackout_proof.core import inspect_pdf


@pytest.mark.parametrize("applied", [False, True])
@pytest.mark.parametrize("blank", [False, True])
def test_pending_redactions_are_value_free(tmp_path, applied, blank):
    source = tmp_path / "synthetic.pdf"
    with pymupdf.open() as document:
        page = document.new_page()
        if not blank:
            page.insert_text((72, 72), "SECRET_CANARY_82641")
        page.add_redact_annot(pymupdf.Rect(60, 50, 300, 85), text="ANNOT_CANARY_38421")
        if applied:
            page.apply_redactions()
        document.save(source)
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    report = inspect_pdf(source)
    pending = [f for f in report["findings"] if f["code"] == "BP008"]
    assert len(pending) == (0 if applied else 1)
    if pending:
        assert pending[0]["severity"] == "warning"
        assert pending[0]["page"] == 1
        assert pending[0]["count"] == 1
        assert "not proof" in pending[0]["message"]
    for format in ("json", "markdown", "html"):
        output = tmp_path / ("report." + format)
        result = main(
            [str(source), "--format", format, "--output", str(output), "--fail-on-findings"]
        )
        assert result == int(bool(report["findingCount"]))
        rendered = output.read_text()
        assert "SECRET_CANARY_82641" not in rendered
        assert "ANNOT_CANARY_38421" not in rendered
        assert ("BP008" in rendered) == (not applied)
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
