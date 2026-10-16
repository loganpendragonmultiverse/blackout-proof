# Blackout Proof

Blackout Proof checks a PDF locally for structural evidence that sensitive material may still be recoverable after redaction.

It reports extractable text intersecting dark opaque covers, populated metadata, embedded files, JavaScript, optional-content layers, interactive forms, and remaining annotations. Reports use counts and locations without repeating document text, metadata values, filenames of attachments, or comments.

## Three-minute start

```bash
python -m pip install .
blackout-proof document.pdf --output redaction-check.md
blackout-proof document.pdf --format json --fail-on-findings
```

## Scope and limitations

- This is a verification aid, not a redaction editor, legal certification, malware scanner, or guarantee that a document is safe.
- Image-only secrets require human visual review; the tool does not perform OCR.
- Opaque-cover detection is conservative and may flag intentional design elements that overlap text.
- Encrypted or damaged PDFs may be unreadable and should fail closed.
- Files never leave the computer; there is no telemetry, network request, or source modification.

Supported on Python 3.10+ for Windows, macOS, and Linux. Current release: **v1.2.0**. Contributions are reviewed through pull requests. MIT licensed.

## Version 1.1.0: reviewed improvements

Add value-free HTML page geometry previews, opt-in local OCR counts and redaction edge-case fixtures.

```bash
blackout-proof sample.pdf --format html --output review.html
```

HTML links page findings to geometry-only previews of dark cover rectangles. To preserve value-free reports, previews omit all source text and imagery rather than embedding source PDF/raster content. --ocr optionally invokes local PyMuPDF/Tesseract OCR and reports only word counts or engine-unavailable status; it is a review aid and never proof of sanitization. Tests generate rotated text/pages, transparent covers, optional layers, applied redactions, encrypted and damaged PDFs and assert source hashes are unchanged. The OCR adapter is tested with controlled success/failure substitutes; native Tesseract acceptance is not claimed. Existing outputs are protected and encrypted PDFs require prior authorized local decryption.


## 1.2.0 — 2026-10-16: Unapplied redaction warnings

Warn with stable code BP008 when unapplied Redact annotations remain. Treat the marker as unfinished redaction, never proof that secret text exists.

BP008 is a warning with the page number and annotation count. It participates in `--fail-on-findings` and appears in JSON, Markdown and HTML. Annotation text, replacement text and underlying document text are never copied into the warning. Applied redactions no longer have pending markers. Stroke-only annotation drawings with no fill opacity are handled without crashing.
