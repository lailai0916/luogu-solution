# Test: Caller Presentation Profile Routing

## Scenario

A caller supplies complete writing, terminology, Markdown, LaTeX, and OI C++ profiles. One of its
binding display-formula rules conflicts with a platform formatting guide, its C++ whitespace rules
are stricter than the bundled fallback, and it also declares sentence length as advisory.

## Expected behavior

- Load every matching caller profile before drafting or implementing.
- Resolve both conflicts in favor of the caller profile without copying its rule manual here.
- Run this Skill's linter in structure-only mode.
- Run the caller owner's checker on both the Markdown draft and standalone C++ source.
- Refuse publication while either artifact violates a binding caller-profile rule.
- Report the sentence-length advice without turning it into a publication failure.

## Failure behavior

Passing compilation, samples, stress tests, or the structural linter does not waive the active
profile. Applying the caller profile as a final cosmetic pass also fails this test.
