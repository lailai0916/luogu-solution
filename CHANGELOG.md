# Changelog

## [Unreleased]

- Scoped new-candidate selection to new solution creation and new live articles. Supplied-draft
  review and bound-article maintenance retain their own routes without weakening correctness,
  originality, current-task authorization, or review-submission gates.
- Added a non-disableable process-wide Luogu request limiter: all requests are serialized with a
  one-second hard interval, authenticated writes use a two-second hard interval, smaller local
  values are ignored, and rate-limit or anti-abuse failures stop instead of entering retry loops.
- Added explicit public-unpublished article maintenance: `--public-only` restores public
  visibility without changing the article, while `--save-public` synchronizes a validated local
  draft. Both force `status: 2`, preserve a non-published `promoteStatus` of `0` or `3`, verify the
  complete read-back, and never create an article, submit code, or request solution review.
- Added explicit personal-hidden article maintenance: `--hide-only` preserves a bound article
  verbatim while making it author-only, and `--save-hidden` synchronizes a validated local draft to
  that same `lid`. Both force Luogu `status: 1`, verify the complete read-back, forbid review
  requests, and cannot create articles. Ambiguous write errors are never retried blindly: an exact
  read-back may establish success, while any mismatch remains a hard stop.
- Added hash-bound local-verification evidence for every verifier run. Hidden-draft synchronization
  now requires a current passing compile/sample record and exact equality between `solution.cpp`
  and the article's single reference-code block; stale or failed evidence stops before networking.
- Made article preservation an absolute lifecycle invariant: wrong, ineligible, rejected, or
  retired solutions keep their original article and `lid`; authorized cleanup empties the content
  or uses a minimal neutral placeholder when Luogu rejects an empty body, but never deletes the
  article. Added the tested `publish.py --retire` interface and kept deletion out of the client.
- Split statement retrieval from reference access, added a pre-reference hash checkpoint, and
  made five-axis originality review a delivery and publication gate; style conversion, notation
  reuse, and structure-preserving paraphrase now fail even when the algorithm is standard. The
  audit is recorded with conclusions for all five axes plus public-source provenance, and is bound
  to the current statement, draft, code, and Luogu-reference set. Stale or missing evidence blocks
  delivery and live publication. A standalone checkpoint command supports public-only review
  without requiring a Cookie or a Luogu reference file.
- Updated the purple minimum from numeric difficulty `6` to `7` for Luogu's June 2026
  eight-tier scale; blue `6` is now an ordinary violation, while below-cyan remains `< 5`.
- Made detailed explanation the default for Luogu solutions: completeness now outranks brevity,
  with explicit derivation, correctness, implementation correspondence, and boundary coverage,
  while standard prerequisites and repetitive padding remain excluded.
- Added a fail-closed official-judge gate before review-bound article writes: the current account
  must have an Accepted record for the same PID whose complete source matches the cached
  `solution.cpp`, and the article reference code must match it; local verification, stale records,
  and different accepted programs do not count.
- Raised the fail-closed candidate gate to purple-or-harder problems and added a deterministic
  two-level violation classifier: ordinary for below-purple or more than three solutions; severe
  for below-cyan, more than five solutions, prior own work, or a closed solution channel.
- Froze the candidate thresholds and complete-account-history check in code: config files,
  environment variables, and batch options cannot weaken the gate.
- Added a fail-closed new-candidate preflight: no more than three existing solutions and no prior
  solution article for the same PID anywhere in the authenticated account's complete article list.
  New live articles rerun the gate before writing; bound-article maintenance remains available.
- Made account-history pagination fail closed on partial non-final pages instead of treating an
  incomplete response as a complete scan.
- Unified the fallback submission target on C++17 with O2, aligned local verification
  with the final language standard, added a judge non-AC repair loop, and separated browser-based
  code submission from API-and-Cookie article synchronization.
- Extended the caller-profile contract from C++ alone to writing, terminology, Markdown, LaTeX,
  and code; caller rules now override bundled and platform formatting defaults from the first
  draft, and both prose and code must pass the profile owner's checker before publication.
- Preserved caller-profile rule strength: binding rules block publication, while explicit
  recommendations remain advisory.
- Added an explicit account-exception path for Agent-generated publication while preserving
  truthful origin classification, current-task authorization, policy confirmation, and read-back.
- Moved review-policy confirmation ahead of all network client construction and article writes,
  covered the ordering with a regression test, and made exception-scoped disclosures explicit.
- Made `题意简述` the normal structure, prohibited every reference-code folding container, and
  added a regression check for the prohibition.
- Reduced the Luogu envelope to the single problem badge so the generic Skill never depends on a
  personal website; made `top: 2` a write-time invariant even under a stale local override and
  verified the top value during publication read-back.
- Clarified that an active caller code profile is a binding implementation contract rather than
  optional guidance or a cosmetic final pass.
- Fixed sample verification for problems whose official output format declares an absolute or
  relative tolerance; exact-output problems remain byte-normalized and exact.
- Added batch pacing and read-back recovery guidance for independent article-creation and
  review-submission `429` responses.
- Added a live `acceptSolution` preflight that stops review-bound publication before any article
  write when Luogu has closed new solutions for the problem.
- Required every body-changing article write to have current hash-bound local verification and
  exact agreement between `solution.cpp` and the article code block. Existing `lid` updates now
  verify the live problem binding before writing, all maintenance read-backs require exact content,
  and review requests are reported successful only after a confirming read-back.

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
