# Solution writing

## Active profile

This file is a compact fallback for callers without a complete presentation profile. If the
caller or target supplies writing, terminology, Markdown, or LaTeX rules, load all matching rules
before drafting and apply them as hard constraints. They override both this fallback and a
platform formatting guide wherever they conflict. Keep those rules at their owner; do not copy
their manuals into this Skill.

## Audience and density

Write for a reader who already knows standard C++ and common OI algorithms. Explain the
problem-specific insight and its proof; do not explain loops, arrays, binary search, ordinary DP,
or other prerequisites unless this problem uses them in an unusual way. Prefer a few dense,
professional paragraphs to a long tutorial.

Do not use filler such as “显然”“不难发现”“众所周知” in place of an argument. State the reason
directly. Do not copy the statement, narrate the writing process, seek likes, address reviewers,
or add personal/AI signatures.

## Structure

The highest heading level inside a solution is H2. Never use H1.

The usual compact structure is:

```markdown
## 题意简述

## 解题思路

## 参考代码
```

Use `题意简述` in most solutions. Compress the task into one or two professional sentences,
without repeating the story or teaching standard notation. Omit it only when the original task is
already a single precise sentence and any restatement would add no information.
Keep the reasoning in complete paragraphs. Use a list only for genuinely parallel or mutually
exclusive cases; do not replace one derivation chain with many tiny headings or bold pseudo
headings.

Correctness belongs next to the step it justifies. A separate proof section is reserved for a
long, genuinely independent proof. Headings below H2 are exceptional and must mark substantial,
independent phases rather than “观察”“状态”“转移”“正确性” fragments.

## Complexity placement

Use the lightest treatment that remains informative:

- If the complexity is immediately visible from the code, omit it. Two plain loops over
  $1\sim n$ do not need a sentence announcing $O(n^2)$.
- If it needs modest composition, add one sentence at the end of `解题思路`, without a heading:
  for example, preprocessing is $O(n\log n)$ and each of $m$ operations is $O(\log n)$.
- Only an unusually difficult analysis—such as a non-trivial amortized proof, analytic
  approximation, or higher-order bound derivation—gets its own H2 section.

Mention space only when it is not obvious or materially constrains the method.

## Formulas and terminology

- Use `$...$` for variables, short equations, and complexity. Use `$$...$$` only for a long
  central formula, aligned derivation, or cases definition that is materially clearer as a block.
- Define each symbol before or immediately when it first appears. Keep state, intervals, and
  indexing identical between prose and code.
- Use established Chinese OI terms: 枚举、转移、维护、预处理、离散化、倍增、松弛、对拍.
  Do not invent labels for a one-off structure.
- Use full-width Chinese punctuation. Put one half-width space between Chinese and Latin text,
  numbers, or formulas, but none before Chinese punctuation.

## Code section

Use an H2 `参考代码` heading and a `cpp` fence. The program must be complete and directly
submittable. Apply the active caller / target code profile when one exists; otherwise use the
compact default in `code-style.md`.

The fenced program is always directly visible. Never wrap reference code in
`::::info[点击展开代码]`, `<details>`, or any other collapsible container, regardless of length.

## Final pass

- The central observation is justified, and every condition in the code appears in the prose.
- No paragraph teaches a standard prerequisite or repeats an earlier conclusion.
- Heading depth is at most H2; structure has not been mechanically fragmented.
- Complexity treatment matches the three-level rule above.
- The reference program is directly visible and has no collapsible wrapper.
- Formula, code, and terminology are consistent; no invented AC or optimality claim appears.
- The active caller / target writing, Markdown, LaTeX, and code checkers all pass; a pass from this
  Skill's structural linter alone never claims profile compliance.
- No AI declaration, promotional footer, reviewer request, or process narration appears in the
  draft. If live publication is requested, apply `publishing.md` separately.
