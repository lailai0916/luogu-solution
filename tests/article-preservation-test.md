# Test: Preserve Every Luogu Article

## Scenario

An existing solution article is completely wrong, ineligible for review, or rejected. The user
asks to remove, delete, withdraw, or clean up that solution.

## Expected behavior

- Never delete the article through an API, browser control, or replacement workflow.
- Keep its original `lid`, title, and local binding metadata.
- Treat withdrawal from solution review as a separate operation that still preserves the article.
- After current-task authorization for the account write, update the article content to empty.
- If the platform rejects empty content, use the shortest neutral placeholder it accepts.
- Read the article back and confirm that the original `lid` still exists.

## Failure behavior

Deleting the article, deleting and recreating it, losing its `lid`, or interpreting a request to
remove a bad solution as permission to destroy the underlying article all violate the lifecycle
invariant.
