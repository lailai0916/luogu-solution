# Test: Detailed Technical Explanation

## Scenario

An experienced contestant could infer several omitted steps in a short draft: why a state is
sufficient, how one transition follows from the invariant, why the construction is complete, and
why the code updates one boundary before another. The draft is otherwise correct and concise.

## Expected behavior

- Expand every omitted problem-specific inference in dependency order.
- Define the state and invariant before using them.
- Derive the transition rather than introducing it as an unsupported formula.
- Explain both legality and completeness next to the relevant algorithm step.
- Connect the boundary and update order to the exact implementation behavior.
- Preserve the established H2 structure and proportional complexity rule.

## Failure behavior

Do not accept the short draft merely because an expert can reconstruct the missing logic. Do not
compensate with a restated problem, C++ syntax instruction, a generic algorithm tutorial, repeated
conclusions, or an arbitrary minimum word count.
