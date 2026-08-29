# Repository instructions

This repository is the canonical source for the runtime-neutral `luogu-solution` Agent Skill.
Read `SKILL.md` before changing behavior, then read every affected file under `references/`,
`scripts/`, `assets/`, and `tests/`.

## Rules

- Keep active guidance runtime-neutral. Describe capabilities rather than one vendor's tool names.
- Luogu is authoritative for statements and current platform rules. Time-sensitive endpoints and
  policies require current verification before they are changed or relied upon for account writes.
- Never store credentials, cache files, generated solutions, or real article payloads in this repo.
- Preserve the source, correctness, read-back, authorization, and publication-eligibility gates.
- `references/code-style.md` is a compact fallback profile. Never copy an external personal style
  manual into this repository; caller / target profiles are applied and validated at their source.
- Python tools follow normal maintainable engineering style and may contain useful comments.
- Keep English and Simplified-Chinese README content aligned.
- A rule or endpoint change requires matching tests and a `CHANGELOG.md` entry.

## Validation

```bash
python3 -m unittest discover -s tests -v
python3 -m py_compile scripts/*.py tests/*.py
```

Also run the active runtime's Agent Skill validator when one is available.

`AGENTS.md` is canonical. `CLAUDE.md` is only a compatibility import; do not duplicate rules in
runtime-specific files.
