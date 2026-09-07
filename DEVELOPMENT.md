# Development handoff

Blackout Proof is a read-only structural verifier. Value-free reports and preservation of the source PDF are hard constraints. Version 1.1 does not edit PDFs, classify legal compliance, or claim that a clean report proves complete sanitization. OCR is explicit opt-in and emits counts only. Detection changes require purpose-built PDFs and false-positive tests.

## 1.1.0 improvement session

Add value-free HTML page geometry previews, opt-in local OCR counts and redaction edge-case fixtures.

HTML links page findings to geometry-only previews of dark cover rectangles. To preserve value-free reports, previews omit all source text and imagery rather than embedding source PDF/raster content. --ocr optionally invokes local PyMuPDF/Tesseract OCR and reports only word counts or engine-unavailable status; it is a review aid and never proof of sanitization. Tests generate rotated text/pages, transparent covers, optional layers, applied redactions, encrypted and damaged PDFs and assert source hashes are unchanged. The OCR adapter is tested with controlled success/failure substitutes; native Tesseract acceptance is not claimed. Existing outputs are protected and encrypted PDFs require prior authorized local decryption.

Local formatting, lint, strict types and regression tests pass. Public release completion requires the protected CI/CodeQL matrix, tagged artifacts and matching Forge catalog/detail deployment.
