# Testing

Run `ruff format --check .`, `ruff check .`, `mypy src`, `pytest`, `python -m build`, and `python -m pip_audit .`. Tests generate PDFs locally and cover dark-cover intersections, metadata, annotations, clean documents, value-free output, hashes, CLI exit behavior, and invalid input.

## 1.1.0 regression acceptance

Run the complete existing suite plus the new regression fixtures. Confirm the documented command produces the selected output, malformed input remains actionable, and source files remain unchanged. Add value-free HTML page geometry previews, opt-in local OCR counts and redaction edge-case fixtures.

## 1.2.0 — 2026-10-16

Generate pending and applied markers over synthetic text and blank areas. Check BP008, all report formats, fail-on-findings, secret canary absence and unchanged source hashes. Run the complete existing PDF regression suite; native OCR acceptance remains unverified.
