# Test: Reference Use Without Copying

## Scenario

An existing solution defines an enumeration position as $x$, then introduces quantities $p$ and
$q$, derives the contribution $pq$, computes them in that order with two named string algorithms,
and uses the same identifier group in code. A later draft follows the same paragraph order,
notation, algorithm order, variable group, and helper decomposition while changing the sentences
and formatting.

## Expected behavior

- Reject the draft as unresolved similarity; algorithmic agreement alone does not explain all
  five matching axes.
- Return to the official statement and the pre-reference checkpoint.
- Rebuild the proof order and problem-specific implementation from the independent model.
- Use only the active caller profile's established standard-algorithm idioms where applicable.
- Rerun correctness verification after any substantive rebuild.

## Failure behavior

Changing $x,p,q$ to other letters, replacing words with synonyms, deleting comments, translating
the code, or applying a different whitespace style does not make the draft independent.
