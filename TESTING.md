# Testing

```bash
python -m pip install -e ".[dev]"
python -m ruff format --check .
python -m ruff check .
python -m mypy src
python -m pytest
python -m build
python -m pip_audit .
```

Keep all original PDF regression assertions and the 90% branch-aware coverage gate.
CI runs Python 3.10 and 3.14 on Linux, Windows and macOS, plus the dependency audit
and CodeQL. The optional native acceptance test is deliberately skipped unless
`BLACKOUT_NATIVE_OCR=1`; ordinary adapter tests still run everywhere.

For real English Tesseract acceptance, install Tesseract/language data in the test
environment and run `BLACKOUT_NATIVE_OCR=1 python -m pytest`. The native test creates
a raster-only synthetic PDF, verifies exactly two OCR words without outputting the
text, then uses a separate process with empty language data to verify incomplete
status, omitted word count and exit 2. It also checks source bytes and absence of
the synthetic phrase in reports/errors. Do not substitute or mock native results.

The suite exercises paint order, literal and escaped PDF names, rotated/transparent
covers, applied and pending redactions, metadata/annotations, encrypted/damaged
PDFs, all report formats, typed API/CLI limits, boundary exhaustion, geometry work,
OCR admission before rasterization, source replacement/change, output aliases,
dangling links, concurrent-file refusal and output I/O failures. All fixtures are
synthetic; never commit private PDFs, native raster output or OCR text.

For each actual tag-workflow wheel and source archive:

1. Compare archive members against exact tagged module sources, all four Markdown
   documents, LICENSE and both example files. Check source archive tests/metadata.
2. Install in a separate fresh environment outside the checkout. Assert
   `blackout_proof.__file__` is inside that environment and remove PYTHONPATH/user
   site fallback. Run the complete exact-tag fixture suite against the installed
   package, retaining the 90% gate and native acceptance where available.
3. Run the installed `share/doc/blackout-proof/examples/make_sample.py` and every
   CLI output mode, budget failure, fail-on-findings, source hash, no-clobber and
   native OCR/missing-data paths. Confirm reports include summary and SHA-256 and
   omit synthetic document/metadata/annotation text and all source imagery.
4. Verify public wheel/source/SHA256SUMS hashes and GitHub digests after upload.

Budgets are not native parser CPU/memory guarantees. Test failures or missing OCR
support must remain visible and must never be relabeled as a successful empty scan.

## 1.3.1 release artifact closure

The Python 3.12 tag workflow checks the stable tag, project metadata and literal
runtime version before building. It repeats the original formatting, lint, strict
typing, full coverage-gated suite and shipped-dependency audit, verifies exact
wheel/sdist names and metadata, and emits SHA256SUMS. Native Linux OCR acceptance,
independent installed-artifact review and public/Forge verification remain separate
required release gates. The workflow does not publish a release automatically.
