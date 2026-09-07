---
name: hermes-continuous-learning
description: Hermes-style auto-write MEMORY/skills + /learn curation on Zed+OMP. Use after durable lessons, hard fixes, user corrections, or when running /learn [topic].
---

# Hermes Continuous Learning

Dual-engine learning loop for Zed + OMP (Hermes parity without native memory tool).

## When to use

- After a non-trivial success, hard bug fix, or user correction
- Explicit `/learn [topic]` force-run
- Always-on rule `hermes-auto-learn` triggers the same contract inline

## Classification

| Class | Target | When |
|---|---|---|
| MEMORY | `~/.katalyst/workspaces/<ws>/MEMORY.md` | Short durable fact / preference / quirk |
| SKILL_NEW | `~/.katalyst/skills/<name>/SKILL.md` | New reusable multi-step procedure |
| SKILL_PATCH | existing `SKILL.md` | New pitfall on near-match skill |
| DISCARD | — | One-off / already captured / not durable |

## Workflow

1. Scan session for durable lessons.
2. Classify MEMORY | SKILL_NEW | SKILL_PATCH | DISCARD.
3. Deduplicate against MEMORY + `~/.katalyst/skills/**/SKILL.md`.
4. Write immediately (no approve gate).
5. Notify one line per write: `💾 Memory updated: ...` or `💾 Skill 'name' created|patched: ...`.
6. MEMORY size guard: if Preferences+Standing decisions exceed ~4000 chars of bullets, consolidate/replace before append.
7. Mirror new skills to `~/.omp/agent/skills/<name>/` when creating; skip inventing a second skill tree for one-off mirrors.

## Never

- Secrets, tokens, keychain values
- Approval elicitation for learning-store writes
- Skill spam on trivial turns
- Background agent every turn for learn (keep inline)
