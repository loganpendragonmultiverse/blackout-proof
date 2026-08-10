from pathlib import Path
from typing import ClassVar

from typing_extensions import Self

import pymupdf
import pytest

from blackout_proof import core
from blackout_proof.cli import main
from blackout_proof.core import _dark_fill, inspect_pdf


def _pdf(
    path: Path, *, covered: bool = False, metadata: bool = False, annotation: bool = False
) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "private words")
    if covered:
        page.draw_rect(pymupdf.Rect(65, 55, 160, 80), color=(0, 0, 0), fill=(0, 0, 0))
    if annotation:
        page.add_text_annot((100, 100), "comment")
    if metadata:
        document.set_metadata({"title": "example"})
    document.save(path)
    document.close()


def test_detects_text_behind_black_rectangle(tmp_path: Path) -> None:
    path = tmp_path / "covered.pdf"
    _pdf(path, covered=True)
    report = inspect_pdf(path)
    assert "BP007" in {item["code"] for item in report["findings"]}  # type: ignore[index]
    assert report["verdict"] == "review"


def test_detects_metadata_and_annotation(tmp_path: Path) -> None:
    path = tmp_path / "annotated.pdf"
    _pdf(path, metadata=True, annotation=True)
    codes = {item["code"] for item in inspect_pdf(path)["findings"]}  # type: ignore[index]
    assert {"BP001", "BP006"} <= codes


def test_clean_pdf_has_hash_and_pages(tmp_path: Path) -> None:
    path = tmp_path / "clean.pdf"
    _pdf(path)
    report = inspect_pdf(path)
    assert report["pageCount"] == 1
    assert len(str(report["sourceSha256"])) == 64


def test_dark_fill_requires_dark_opaque_color() -> None:
    assert _dark_fill({"fill": (0.1, 0.1, 0.1), "fill_opacity": 1})
    assert not _dark_fill({"fill": (1, 1, 1), "fill_opacity": 1})
    assert not _dark_fill({"fill": None})


def test_cli_writes_value_free_json(tmp_path: Path) -> None:
    path = tmp_path / "covered.pdf"
    output = tmp_path / "report.json"
    _pdf(path, covered=True)
    assert main([str(path), "--format", "json", "--output", str(output), "--fail-on-findings"]) == 1
    text = output.read_text(encoding="utf-8")
    assert "private words" not in text
    assert '"BP007"' in text


def test_cli_rejects_non_pdf(tmp_path: Path) -> None:
    path = tmp_path / "note.txt"
    path.write_text("x", encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        main([str(path)])
    assert raised.value.code == 2


def test_cli_prints_markdown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "clean.pdf"
    _pdf(path)
    assert main([str(path)]) == 0
    assert "Blackout Proof report" in capsys.readouterr().out


def test_structural_object_findings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class Annotation:
        type = (0, "Text")

    class Page:
        def annots(self) -> list[Annotation]:
            return [Annotation()]

        def get_drawings(self) -> list[object]:
            return []  # placeholder-detector: ignore

        def get_text(self, _kind: str) -> list[object]:
            return []  # placeholder-detector: ignore

    class Document:
        metadata: ClassVar[dict[str, str]] = {"title": "x"}
        is_form_pdf = 1
        page_count = 1

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def embfile_names(self) -> list[str]:
            return ["hidden.bin"]

        def xref_length(self) -> int:
            return 3

        def xref_object(self, xref: int, compressed: bool = True) -> str:
            return "/JavaScript" if xref == 1 else "/OCG"

        def __iter__(self) -> object:
            return iter([Page()])

    path = tmp_path / "synthetic.pdf"
    path.write_bytes(b"%PDF-test")
    monkeypatch.setattr(core.pymupdf, "open", lambda **_kwargs: Document())
    codes = {item["code"] for item in inspect_pdf(path)["findings"]}  # type: ignore[index]
    assert {"BP001", "BP002", "BP003", "BP004", "BP005", "BP006"} <= codes
