<div align="center">
  <h1>Luogu Solution</h1>
  <p><strong>English</strong> · <a href="README.zh-Hans.md">简体中文</a></p>
  <p>
    <img src="https://img.shields.io/github/actions/workflow/status/lailai0916/luogu-solution/ci.yml?branch=main&style=flat-square" />
    <img src="https://img.shields.io/github/last-commit/lailai0916/luogu-solution?style=flat-square" />
    <img src="https://img.shields.io/github/languages/top/lailai0916/luogu-solution?style=flat-square" />
    <img src="https://img.shields.io/github/repo-size/lailai0916/luogu-solution?style=flat-square" />
    <img src="https://img.shields.io/github/license/lailai0916/luogu-solution?style=flat-square" />
  </p>
</div>

## Project Introduction

A runtime-neutral Agent Skill for the complete Luogu solution workflow: retrieve the official
statement, study accessible references, derive and verify an algorithm, stress test it, write a
concise Chinese solution, and safely create or synchronize a Luogu article.

## Project Features

- **Official source first** — Luogu remains authoritative for statements, limits, samples, and
  current submission rules.
- **Correctness before prose** — proof, compilation, samples, boundary cases, and deterministic
  stress testing form one workflow.
- **Dense OI writing** — H2-only solution structure, problem-specific explanation, and
  proportional complexity analysis.
- **Composable GNU C++14 style** — a compact default profile plus clean replacement by a caller or
  target repository's own OI style, without copied rule manuals.
- **Safe account operations** — local credentials, explicit live authorization, full read-back,
  and a current platform-policy or account-exception gate before review submission.

## Getting Started

```bash
git clone https://github.com/lailai0916/luogu-solution ~/.agents/skills/luogu-solution
cd ~/.agents/skills/luogu-solution
python3 -m pip install -r requirements.txt
python3 scripts/fetch.py P1001
```

Place an optional Luogu Cookie in `~/.config/luogu-solution/cookie.txt` with mode `0600`, or set
`LUOGU_COOKIE`. Generated work stays under `~/.cache/luogu/<PID>/` and never enters this repo.

## Project Structure

```bash
luogu-solution/
├── agents/                     # Skill UI metadata
├── assets/                     # Reusable OI code template
├── references/                 # Workflow, writing, code, publishing rules
├── scripts/                    # Fetch, verify, stress, and publish tools
├── tests/                      # Offline deterministic unit tests
└── SKILL.md                    # Runtime-neutral Skill entrypoint
```

## License

This project's code is licensed under [MIT License](https://github.com/lailai0916/tools/blob/main/LICENSE).
