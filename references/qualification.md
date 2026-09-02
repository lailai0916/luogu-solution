# Candidate qualification and violation audit

This file is the single source for hard candidate thresholds and retrospective violation
classification. The thresholds are implemented by `scripts/candidate.py` and are deliberately
not runtime-configurable.

## New-candidate gate

Run the complete gate before creating code, prose, a brute force, or a generator, and rerun it
immediately before creating a live article. The default policy requires all of the following:

- a rated Luogu theme-bank problem with difficulty at least purple (`difficulty >= 7`);
- an open solution channel (`acceptSolution: true`);
- no more than three existing public solutions;
- no earlier solution article for the PID anywhere in the authenticated account's complete
  `我的专栏` history.

The gate is fail-closed. A missing or unparseable live field, incomplete account history, expired
login, or failed request is a rejection, not permission to continue. Local ledgers, site indexes,
cached misses, downloaded-reference counts, accepted-problem lists, and public-solution absence
cannot replace the corresponding live check. Qualification must finish before parallel solving or
writing starts.

No config file, environment variable, batch option, or caller preference may lower the minimum
difficulty, raise the public-solution limit, skip the open-channel check, or disable the complete
account-history check. A future policy change must edit this source, the constants, and their tests
together.

## Two-level violation classification

When auditing existing work, classify each article against one consistent snapshot. Serious
conditions override ordinary ones.

| Level | Conditions |
| --- | --- |
| Ordinary | difficulty below purple (`< 7`), or solution count greater than `3` |
| Severe | difficulty below cyan (`< 5`), solution count greater than `5`, an earlier own solution, or a closed solution channel |

The current numeric scale, introduced when Luogu added the cyan tier in June 2026, is red `1`,
orange `2`, yellow `3`, green `4`, cyan `5`, blue `6`, purple `7`, and black `8`; `0` is unrated.
Do not reuse the former seven-tier mapping, where purple was `6`.

For account history, exclude the article currently being audited, then search the complete account
history for an earlier article with the same PID. Report overlapping reasons separately while
counting each article once at its highest level.

Use `classify_violation` from `scripts/candidate.py` when a deterministic classification is needed.
It returns the highest level plus separate ordinary and severe reason lists from these hard
thresholds.

Current solution count and pre-publication solution count answer different questions. A current
count can include the audited article after approval. Use a timestamped live count for current-state
reports; use preserved pre-publication evidence for claims that the original selection exceeded the
limit. Label the chosen basis and never mix the two in one count.

## Review-state audit

Do not infer review state from a local task label. Read the complete current article list and, when
an article is no longer in the review queue, use account notifications to distinguish rejection,
withdrawal after approval, and a review request that never succeeded. Timestamp every batch report
because review states and public solution counts can change during the audit.
