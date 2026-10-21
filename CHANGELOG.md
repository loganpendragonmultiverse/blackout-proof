# Changelog

## 1.3.0 - 2026-10-21

- Exclude technical PDF format/encryption descriptors from BP001, count XMP packet presence without values, and refuse FIFO inputs before opening.

- Compare stat and fstat metadata within their own before/after snapshots, avoiding confirmed Windows Python 3.14 ctime representation mismatches while retaining identity/hash checks.
- Refuse PDFs that require native structural repair; cap native read sizes even with huge valid budgets.
- Add typed file, page, xref, serialized-object, page-item, geometry-work and OCR-pixel budgets; refuse incomplete inspections and changed source identities/bytes.
- Count extractable glyph instances using their own paint sequence, fixing foreground-word overcounting; respect paint order when checking dark covers and exclude literal/hex/comment text from PDF object-name checks, fixing confirmed real-PDF false positives.
- Make requested OCR failures explicitly incomplete with exit 2, count-only results and native English Tesseract/missing-data regression acceptance.
- Create reports exclusively, refuse source aliases and existing links, handle output failures, and escape source identifiers in Markdown/HTML.
- Add complete document summaries/source fingerprints to HTML and OCR statuses to Markdown; package synthetic examples with the documentation.
- Retain Python 3.10+ and require audited PyMuPDF 1.28.2+ within 1.x; clarify its separate AGPL/commercial licensing.

## 1.2.0 - 2026-10-16

- Warn with stable code BP008 when unapplied Redact annotations remain. Treat the marker as unfinished redaction, never proof that secret text exists.
- Handle stroke-only pending annotation drawings without a fill-opacity crash.

## 1.1.0 - 2026-09-07

- Add value-free HTML page geometry previews, opt-in local OCR counts and redaction edge-case fixtures.
- Added regression coverage for the audited behavior and invalid inputs.

## 1.0.0 - 2026-08-10

- Added local PDF structural redaction verification.
- Added residual-text, metadata, attachment, script, layer, form, and annotation findings.
- Added value-free Markdown and JSON reports with source fingerprints and CI exit behavior.
