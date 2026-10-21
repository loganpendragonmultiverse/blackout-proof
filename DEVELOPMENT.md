# Development handoff

Blackout Proof is a read-only structural verifier. Value-free reports and source
preservation are hard constraints. Keep it separate from PDF editing/redaction,
legal compliance classification, malware scanning and automated truth judgments.
OCR is explicit opt-in, and reports contain counts only. Do not include source PDF
text, image previews, metadata values, attachment names or annotation comments.

Before changing detection, reproduce the behavior using synthetic real PDFs and
include a false-positive test. BP007 uses each traced glyph
span's own `seqno` and the drawing's `seqno`; a prior background is not a later cover. See the
[upstream API](https://pymupdf.readthedocs.io/en/latest/functions.html#Page.get_texttrace).
PDF object-name scanning excludes strings, hex strings and comments, and decodes
escaped name bytes. Structural names do not prove execution or sensitive content.

Keep file/page/xref/object/item/geometry/OCR budgets explicit and positively typed.
Never turn an exhausted limit or failed requested OCR into a clean verdict. Native
PDF operations may allocate/work before a returned result can be bounded; do not
claim CPU/memory isolation. Recheck source bytes and identities before returning.
New report files must not overwrite existing files or existing symbolic links.

Use the six-platform/runtime CI matrix, strict typing, full branch-aware suite,
dependency audit and CodeQL. Preserve their thresholds and required review/checks.
Native OCR acceptance is a separate real-engine gate; adapter substitutes are not
native proof. Retain Python 3.10 compatibility and the supported, audited PyMuPDF
1.x range unless a separately authorized support change is made. Project MIT
licensing does not cover PyMuPDF's AGPL/commercial terms.

Release the exact protected squash commit through an annotated tag. Verify both
tag-built archives contain the exact docs, sources, tests and examples, then run
full suites and installed-example/native OCR acceptance outside the checkout with
installed import-origin assertions. Verify public asset hashes, descriptions and
Forge catalog/details before calling the release complete. No autonomous releases.

## 1.3.1 release artifact closure

The Python 3.12 tag workflow checks the stable tag, project metadata and literal
runtime version before building. It repeats the original formatting, lint, strict
typing, full coverage-gated suite and shipped-dependency audit, verifies exact
wheel/sdist names and metadata, and emits SHA256SUMS. Native Linux OCR acceptance,
independent installed-artifact review and public/Forge verification remain separate
required release gates. The workflow does not publish a release automatically.
