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

Supported on Python 3.10+ for Windows, macOS, and Linux. Current release: **v1.0.0**. Contributions are reviewed through pull requests. MIT licensed.
