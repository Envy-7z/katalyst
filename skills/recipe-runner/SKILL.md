---
name: recipe-runner
description: Standardized task automation, multi-step engineering SOPs, and verification flows via .katalyst/recipes/*.yaml. Use when running pre-PR checks, security audits, database parity checks, or repetitive multi-step verification.
---

# Recipe Runner (Automated Engineering SOPs)

Standardized task execution inspired by Block Goose's recipes, tailored for Katalyst workflows.

## 1. What Are Task Recipes?

Recipes are deterministic, declarative YAML workflows stored in `.katalyst/recipes/<name>.yaml` (project-scoped) or `~/.katalyst/recipes/<name>.yaml` (global).

They combine:
- Automated terminal commands (`run: <command>`)
- Agent verification directives (`prompt: <instruction>`)

## 2. Using `katalyst-recipe` CLI

- **List available workflows**:
  ```bash
  katalyst-recipe list
  ```
- **Execute a workflow**:
  ```bash
  katalyst-recipe run pre-pr-check
  ```
- **Create a new starter recipe**:
  ```bash
  katalyst-recipe create mobile-audit
  ```

## 3. Standard Recipe Schema

```yaml
name: pre-pr-check
description: "Full automated pre-PR verification suite"
steps:
  - run: "git diff --check"
    description: "Check for conflict markers and whitespace anomalies"
  - run: "python3 -m unittest discover -s tests -q"
    description: "Execute regression test suite"
  - run: "bash scripts/audit-privacy.sh"
    description: "Enforce zero-leak security guard"
  - prompt: "Review the current staged diff, summarize changes, and confirm readiness for PR creation."
```

## 4. Best Practices for Recipes

- **Fail-Fast**: Put fast deterministic sanity checks (`git diff --check`, linting) before long-running integration suites.
- **Idempotency**: All `run:` commands should be safe to execute multiple times.
- **Agent Handoff**: End the recipe with a clear `prompt:` directive specifying what the coding agent should review or report.
