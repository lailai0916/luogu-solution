# Default GNU C++14 profile

## Scope

This is the Skill's compact fallback profile, not a second copy of any user's complete code
style. If the caller or target repository supplies an OI code profile, apply that profile as a
whole and run its checker; do not mirror its rules here or merge conflicting micro-conventions.

The executable default is [`assets/main.cpp`](../assets/main.cpp). Keep that asset, the default
checks in `scripts/lint.py`, and their tests aligned.

## Default choices

- Use GNU C++14, `#include <bits/stdc++.h>`, and `using namespace std;`.
- Indent with one Tab. Put ordinary braces on their own lines; a single short statement may stay
  inline without braces.
- Keep the program compact and directly submittable. Remove debugging code, defensive scaffolding,
  and comments; explanation belongs in the solution prose.
- Prefer `cin` / `cout`, add fast I/O when needed, write newlines as `<<'\n'`, and end `main` with
  `return 0;`.
- Prefer appropriately sized scalar types, global static arrays for large fixed storage, and short
  conventional contest names. The bundled default uses `f` for DP state rather than `dp`.
- Keep formulas, indices, intervals, and identifiers consistent between prose and code.

These choices define the bundled example only. Correctness, GNU C++14 compatibility, and complete
submittability remain workflow requirements under every profile.

## Validation

Run the normal linter to apply the bundled profile:

```bash
python3 scripts/lint.py P1001
```

When another explicit code profile is active, validate structure here and style at its source:

```bash
python3 scripts/lint.py P1001 --structure-only
```
