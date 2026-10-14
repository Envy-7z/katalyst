---
name: annotate-diff
description: Batch diff review and multi-file feedback consolidation (Orca ADE diff-comments pattern). Use when reviewing AI-generated diffs, providing multi-line anchored feedback, or handling batch code review notes without conversational thrashing.
---

# Annotate Diff (Batch Review Feedback)

An architectural workflow pattern inspired by Orca's `diff-comments` subsystem, eliminating line-by-line thrashing and multi-turn conversational ping-pong.

## 1. Core Principle

Instead of prompting the agent back-and-forth for every individual typo, rename, or missing error check:
1. Developers inspect the unified diff (`katalyst-review diff` or editor diff pane).
2. Record line-anchored notes across multiple files (`katalyst-review note <file> <range> "<msg>"`).
3. Bundle all review notes into a single, cohesive revision turn (`katalyst-review bundle`).
4. The agent consumes the entire review packet and applies all fixes atomically.

## 2. CLI Workflow (`katalyst-review`)

- **View Diff**:
  ```bash
  katalyst-review diff
  ```
- **Record Notes**:
  ```bash
  katalyst-review note src/auth.ts 42-45 "Add null check before accessing bearer token"
  katalyst-review note src/api.ts 110 "Handle HTTP 429 exponential backoff retry"
  ```
- **Inspect Pending Notes**:
  ```bash
  katalyst-review list
  ```
- **Generate AI Prompt Bundle**:
  ```bash
  katalyst-review bundle
  ```
- **Clear Notes After Application**:
  ```bash
  katalyst-review clear
  ```

## 3. Agent Protocol for Consuming Batched Review

When receiving a batch diff review bundle:
1. **Analyze All Notes First**: Read all comments before editing to understand cross-file implications.
2. **Apply in Order of Dependency**: Update interfaces and schemas first, then implementation logic.
3. **Run Regression Tests**: Execute unit tests after all edits are applied.
4. **Report Verification**: List each addressed review note with proof of validation.
