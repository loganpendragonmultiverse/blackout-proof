"""Create a small synthetic PDF for the Blackout Proof three-minute example."""

from __future__ import annotations

import argparse
from pathlib import Path

import pymupdf


def create_sample(output: Path, *, raster: bool = False) -> None:
    with pymupdf.open() as document:
        page = document.new_page(width=600, height=200)
        page.insert_text((40, 100), "EXAMPLE REVIEW", fontsize=32)
        if raster:
            image = page.get_pixmap().tobytes("png")
            document.delete_page(0)
            page = document.new_page(width=600, height=200)
            page.insert_image(page.rect, stream=image)
        else:
            page.draw_rect(pymupdf.Rect(30, 60, 430, 110), fill=(0, 0, 0))
        document.set_metadata({})
        raw = document.tobytes()
    if output.is_symlink():
        raise ValueError("sample output must not be a symbolic link")
    with output.open("xb") as stream:
        stream.write(raw)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--raster", action="store_true")
    args = parser.parse_args()
    create_sample(args.output, raster=args.raster)
