# Blackout Proof

Blackout Proof checks a local PDF for structural evidence that material may remain
recoverable after redaction. It is for people reviewing a document before sharing
it. Reports contain counts, page numbers and cover geometry, with no document text,
metadata values, attachment names, annotation comments or source imagery.

Current release: **v1.3.0**. Requires Python **3.10+** on Windows, macOS or Linux.

## Three-minute start

```bash
python -m pip install .
python examples/make_sample.py sample.pdf
blackout-proof sample.pdf --format html --output review.html
blackout-proof sample.pdf --format json --fail-on-findings
```

The synthetic sample intentionally leaves two extractable words behind a dark
rectangle. For a real review, substitute your own PDF. JSON is suitable for local
automation; Markdown is a compact checklist; HTML adds geometry-only page previews.
HTML and Markdown both identify the source basename, SHA-256, page/finding counts,
completion status and verdict. HTML lists document-level findings once, then links
to each page's geometry and OCR status. Rectangles are review regions, not proof of
failed sanitization.

Install a downloaded release wheel with `python -m pip install <wheel-file>`.
Documentation and the synthetic example generator are also installed under
`share/doc/blackout-proof` in the Python environment prefix.

## What is checked

| Code | Evidence |
|---|---|
| BP001 | Populated document metadata fields |
| BP002 | Embedded files |
| BP003 | Interactive form content |
| BP004 | JavaScript-related PDF names in object structure |
| BP005 | Optional-content layer objects |
| BP006 | Non-redaction annotations |
| BP007 | Extractable glyph instances intersecting a later dark opaque drawing |
| BP008 | Unapplied Redact annotations |

BP007 counts non-whitespace glyph instances reported by PyMuPDF text traces, not
words. Each glyph is matched using its own paint sequence and bounding box; a later
foreground word is not attributed to an unrelated earlier text span. Repeated paint
operations may contribute separate glyph instances. BP007 respects paint order: text painted after a dark background does not count as
text behind that background. Geometry remains conservative; complex shapes,
clipping, optional layers and partially intersecting glyphs require visual review.
BP004/BP005 inspect PDF name tokens, excluding literal strings, hex strings and
comments. A name is structural evidence to review, not proof that a script executed
or that a layer contains sensitive data. BP008 means unfinished redaction markers,
not proof that secret text exists. Applied redactions no longer have those markers.

## Optional local OCR

```bash
python examples/make_sample.py raster.pdf --raster
blackout-proof raster.pdf --ocr --format json --output ocr-review.json
```

OCR is **off by default**. `--ocr` uses PyMuPDF with local Tesseract English language
data and a fixed 150 DPI raster. Only status and word count appear in reports; OCR
text and raster images are never included. With the supplied raster sample and
working English data, the expected count is two words. Native acceptance exercised
real Tesseract on Linux, including a missing-language-data case; the ordinary
cross-platform suite also tests the adapter with controlled success/failure cases.
Native Tesseract operation on Windows/macOS remains dependent on the user's local
installation and is not claimed by the Python CI matrix alone.

Missing data or an OCR failure sets `inspectionComplete` to false and the verdict
to `incomplete`, omits `word_count`, and exits **2** even without
`--fail-on-findings`. An unavailable engine is never reported as zero words.
Use Tesseract's normal local language-data installation or `TESSDATA_PREFIX`.

## Bounded inspection and source preservation

The API accepts `InspectionLimits`; each field must be a positive integer, and
`ocr` must be a boolean. CLI limits use the corresponding hyphenated options:

| Option | Default |
|---|---:|
| `--max-file-bytes` | 33,554,432 (32 MiB) |
| `--max-pages` | 1,000 |
| `--max-xrefs` | 100,000 |
| `--max-object-chars` | 8,388,608 combined serialized object characters |
| `--max-page-items` | 100,000 for each page's extracted item list |
| `--max-geometry-checks` | 1,000,000 geometry loop steps per page |
| `--max-ocr-pixels` | 20,000,000 raster pixels per page |
| `--max-total-ocr-pixels` | 100,000,000 raster pixels across the document |

File reads are bounded; page/xref budgets are checked before their loops, and the
OCR raster budget is checked before rasterization. Exceeding a budget produces no
complete report and exits 2. Budgets limit admission and this tool's work; they do
not guarantee CPU time or native-library memory use. Native parsing/decompression
and extraction happen before some returned-list sizes can be checked. This is not
a hardened sandbox for hostile files.

The source is opened read-only and fingerprinted. Its open-file identity, path
identity and bytes are checked again before a report is returned. A changed source
is refused. Output must be a new file distinct from the source; existing symbolic
links are refused and file creation is exclusive. This prevents accidental
clobbering, not hostile concurrent filesystem changes.

Exit 0 means a complete report was produced; findings may still exist. Add
`--fail-on-findings` to return 1 for findings. Exit 2 means invalid input, exhausted
limits, unreadable/encrypted/damaged/empty PDF, unavailable requested OCR, changed
source or output failure. Incomplete OCR reports retain structural findings for
review; other inspection failures do not produce a report.

## Boundaries, privacy and licensing

This is a verification aid, **not a PDF editor, redactor, legal certification,
malware scanner or guarantee that a document is safe**. A clean structural report
and a successful OCR count do not prove sanitization. Image-only material still
needs visual review. Encrypted PDFs require prior authorized local decryption.
Files stay on your computer; the tool makes no network requests or telemetry calls
and never modifies its source PDF.

Blackout Proof's own source is [MIT licensed](LICENSE). The required
[PyMuPDF dependency](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)
is separately dual licensed under GNU AGPL 3.0 or an Artifex commercial license;
this repository's MIT license does not relicense that dependency. Optional system
Tesseract has its own [Apache 2.0 license](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE).
Review those dependencies' terms for your use and distribution.

See [DEVELOPMENT.md](DEVELOPMENT.md), [TESTING.md](TESTING.md),
[CONTRIBUTING.md](CONTRIBUTING.md) and [SECURITY.md](SECURITY.md). Changes are maintained
through reviewed pull requests; there is no automatic release or monitoring promise.
Part of the [Forge open-source collection](https://www.loganpendragonforge.com/open-source/).
