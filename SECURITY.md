# Security policy

Security fixes target the latest Blackout Proof release (currently 1.3.x). Report
vulnerabilities privately through GitHub security advisories; do not open a public
issue for an undisclosed vulnerability or attach confidential PDFs.

Blackout Proof parses untrusted PDFs locally. It never edits the source, and its
reports must contain only counts, geometry, source identity and fixed diagnostics.
Use synthetic fixtures for reporting parser failures or content disclosure.

Explicit budgets and source/output checks reduce accidental resource exhaustion
and overwrites. They do not sandbox native PyMuPDF/Tesseract parsing, guarantee
CPU/memory limits, prove sanitization or defend against hostile concurrent
filesystem changes. Keep separately licensed native dependencies up to date.
