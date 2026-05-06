# Categorize Artifact Rules

Use when creating or updating a categorize artifact.

Create a Markdown artifact whenever there are reconciliation findings, pending or answered questions, blockers, warnings, memory suggestions, or posting inputs too large for a compact return. For trivial no-blocker work, returning without an artifact is allowed.

Rules:

- Read `categorize-artifact.example.md` before creating the artifact.
- Write under `.auto-bean/artifacts/categorize/`.
- Use the shared raw-statement artifact prefix, such as `.auto-bean/artifacts/categorize/<artifact_prefix>--categorize.md`.
- Make the artifact directly fillable by a non-technical user with concise summaries, clear sections, stable question ids, checkboxes for choices, short blanks for account/category names, and explicit "leave blank if unknown" guidance where appropriate.
- Include source parsed statement path, statement/status id, categorization results, reconciliation and deduplication findings, pending and answered user questions, warnings, blockers, and memory suggestions.
- Preserve any clearly labeled `Import Batch Cross-Statement Review` section that `$auto-bean-import` appended after categorization.
- Keep user-editable fields visibly separated from observed facts and agent suggestions.
- Keep artifacts factual and reviewable; follow shared artifact privacy and ownership boundaries.
