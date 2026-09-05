# Independent derivation and originality

Existing solutions are untrusted review material, not a drafting substrate. Algorithmic
convergence is sometimes inevitable; duplicated exposition, notation, implementation choices, or
code is not.

## Phase separation

1. Fetch and read only the official statement.
2. Independently finish the proof, `solution.cpp`, and a complete `solution.md` draft.
3. Before reading any reference, run `python3 scripts/originality.py <PID> --checkpoint`. When
   Luogu references are available, `python3 scripts/fetch.py <PID> --references` performs the
   same checkpoint automatically before its request.
4. Read references only as adversarial review: search for missed cases, invalid assumptions,
   complexity traps, and genuinely better algorithms.
5. Reverify every accepted correction from the statement. Never let a reference become authority
   merely because its code is Accepted.
6. Record the completed five-axis comparison with
   `python3 scripts/originality.py <PID> --report <REPORT.json>`. Delivery and publication require
   that report to match the current statement, draft, code, and fetched-reference set.

Do not browse public editorials, code, or discussions before the independent checkpoint. If the
problem cannot be solved independently, report that limitation instead of disguising a reference
solution as an independent one.

## Historical remediation

An old draft that was written after references had already been opened must never receive a fake
pre-reference checkpoint. Before changing that draft, run:

```bash
python3 scripts/originality.py <PID> --start-remediation
```

This seals the official statement, fetched-reference set, and both contaminated baseline
artifacts. The remediation path then requires both `solution.cpp` and `solution.md` to be rebuilt;
changing only names, formatting, or isolated sentences is not sufficient semantic remediation.
After the rebuild, compare all five axes and record the ordinary report. The resulting audit states
`post-reference-remediation` explicitly and remains hash-bound to the baseline checkpoint,
reference set, and final artifacts.

This exception exists only for honest repair of already exposed historical material. New work must
use the pre-reference independent checkpoint. If an independent checkpoint already exists, the
remediation command refuses to replace it.

## Forbidden transfer

Never copy, translate, lightly paraphrase, or style-convert another solution. In particular, do
not carry over a reference's:

- paragraph or proof order, especially a distinctive sequence of observations;
- private notation, symbol bundle, case split, example, diagram, or analogy;
- variable bundle, helper names, function boundaries, data layout, or control-flow skeleton;
- code with only whitespace, naming, comments, language, or surface syntax changed;
- expression assembled from fragments of several references.

Standard theorem names, unavoidable formulas, conventional data-structure operations, and an
active caller profile's established personal templates may coincide. Their use does not justify
copying the problem-specific glue around them.

## Reference-aware audit

After reference review, compare the final draft against every fetched source along five axes:

1. derivation and paragraph order;
2. notation and introduced symbols;
3. examples, cases, and correctness argument;
4. variable groups and helper decomposition;
5. code statement order and control flow.

When several axes overlap beyond what the algorithm forces, return to the statement and rebuild
the explanation and implementation from the independent model. Renaming variables or replacing
words is not a repair. If the same algorithm remains best, preserve the independent proof order
and implement its standard components through the active caller profile's canonical idioms.

The report is evidence of an actual semantic review, not a checkbox. It is a JSON object with a
non-empty conclusion for every axis:

```json
{
  "derivation_order": "...",
  "notation": "...",
  "examples_and_correctness": "...",
  "variables_and_helpers": "...",
  "code_control_flow": "...",
  "public_sources": [
    {
      "url": "https://example.com/reference",
      "title": "Reference title"
    }
  ]
}
```

List every non-Luogu public editorial, discussion, or code source that was read. Public-only review
does not require a Cookie or a `raw/solutions.json` file, but it does require the independent
checkpoint to exist before the first public source is opened. The recorder
deduplicates those URLs and binds the resulting ledger to the current artifacts. Do not use a
generic conclusion such as “checked, no copying”: state what was compared and why any remaining
similarity is forced by the algorithm or the active personal profile. The script verifies
completeness and hashes; it cannot replace the reviewer’s semantic judgment.

Run `python3 scripts/originality.py <PID> --check` before delivery. Any change to the official
statement cache, `solution.md`, `solution.cpp`, `raw/solutions.json`, or the public-source ledger
invalidates the audit and requires a fresh comparison.

Unresolved similarity blocks delivery, article synchronization, and review submission. A
structural linter, compiler, stress test, or Accepted verdict never establishes originality.
