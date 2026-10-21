# Synthetic examples

Generate a PDF containing only the words EXAMPLE REVIEW, then inspect it:

```bash
python examples/make_sample.py sample.pdf
blackout-proof sample.pdf --format html --output sample-review.html
blackout-proof sample.pdf --format json --fail-on-findings
```

The cover is deliberately drawn after the text, so BP007 should be present. The
example never edits an existing file. For opt-in native OCR, create a raster-only
version with `python examples/make_sample.py raster.pdf --raster` and run
`blackout-proof raster.pdf --ocr --format json`. With local English Tesseract data,
OCR should complete with two words; reports contain only the count. An unavailable
engine produces an incomplete report, not a zero-word success.

Installed examples are under `share/doc/blackout-proof/examples` in the Python
environment prefix. No private input or source PDF/raster is included in reports.
