# Changelog

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
