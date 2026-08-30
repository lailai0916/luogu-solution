# Changelog

## [Unreleased]

- Changed the fallback submission target to `C++14 (GCC 9)` with O2, aligned local verification
  with the final language standard, added a judge non-AC repair loop, and separated browser-based
  code submission from API-and-Cookie article synchronization.
- Extended the caller-profile contract from C++ alone to writing, terminology, Markdown, LaTeX,
  and code; caller rules now override bundled and platform formatting defaults from the first
  draft, and both prose and code must pass the profile owner's checker before publication.
- Added an explicit account-exception path for Agent-generated publication while preserving
  truthful origin classification, current-task authorization, policy confirmation, and read-back.
- Moved review-policy confirmation ahead of all network client construction and article writes,
  covered the ordering with a regression test, and made exception-scoped disclosures explicit.
- Made `题意简述` the normal structure, prohibited every reference-code folding container, and
  added a regression check for the prohibition.
- Restored the exact two-badge Luogu envelope, made `top: 2` a write-time invariant even under a
  stale local override, and verified the top value during publication read-back; lailai's Home
  remains badge-free and uses frontmatter `lid`.
- Clarified that an active caller code profile is a binding implementation contract rather than
  optional guidance or a cosmetic final pass.
- Fixed sample verification for problems whose official output format declares an absolute or
  relative tolerance; exact-output problems remain byte-normalized and exact.
- Added batch pacing and read-back recovery guidance for independent article-creation and
  review-submission `429` responses.

## [1.0.0] - 2026-08-30

- Created a standalone, runtime-neutral Luogu solution workflow.
- Integrated official-statement retrieval, optional reference retrieval, local verification,
  deterministic stress testing, concise solution writing, article creation/update, read-back,
  and guarded review submission.
- Added a compact default GNU C++17 OI profile, including comment-free code and `f` for DP,
  while allowing an explicit caller / target profile to replace it without copied rule manuals.
- Added current Luogu policy and task-specific authorization gates for account writes.
- Added a deterministic solution linter for heading depth, required sections, default-profile code
  checks, code fences, and generic AI signatures; `--structure-only` delegates style to its owner.
- Added Python 3.9 and 3.13 CI plus a narrow macOS system-Python compatibility constraint for
  `urllib3` 1.26.20, avoiding LibreSSL warnings without holding back modern environments.
