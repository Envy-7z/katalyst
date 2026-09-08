---
name: andrej-karpathy-skills
description: Karpathy's golden heuristics for AI coding agents. Prevents over-engineering, sycophancy, silent assumptions, hallucinated APIs, and bloated abstractions. Enforces surgical diffs, mental models, and empirical verification. Use when planning, implementing non-trivial logic, refactoring, or reviewing AI-generated code.
---

# Andrej Karpathy AI Coding Skills

Grounded in Andrej Karpathy's public principles and documented heuristics for AI-assisted programming. Designed to eliminate the primary failure modes of LLMs: over-confidence, premature abstraction, sycophancy, and unverified hallucinations.

---

## The 4 Golden Principles

```
   ┌─────────────────────────────────────────────────────────┐
   │ 1. THINK BEFORE CODING (Surface Tradeoffs & Assumptions)│
   │ 2. SIMPLICITY FIRST    (Boring, Explicit, Anti-Bloat)   │
   │ 3. SURGICAL CHANGES    (Minimal Diffs, Zero Drive-bys)  │
   │ 4. GOAL-DRIVEN CHECKS  (Empirical Runtime Verification) │
   └─────────────────────────────────────────────────────────┘
```

### 1. Think & Specify Before Coding
- **Build a Mental Model First**: Do not generate code while still guessing the data flow. Trace inputs, state transitions, and edge cases before touching files.
- **Surface Tradeoffs Explicitly**: Never make silent architectural compromises. If Approach A is simple but has edge case X, and Approach B covers X by adding 3 layers of abstraction, name the tradeoff directly.
- **Resist Sycophancy**: Do not blindly agree with flawed user suggestions. If an instruction weakens security, leaks memory, or breaks existing invariants, state the risk with evidence and propose a better alternative.

### 2. Simplicity First (Anti-Over-Engineering)
- **Prefer Boring Code**: Plain, explicit procedural code is 10x easier to debug than clever metaprogramming, generic reflection, or speculative factory hierarchies.
- **The Rule of Three**: Three duplicated lines of clear, localized code are strictly better than an over-engineered, leaky abstraction.
- **No Speculative Architecture**: Do not add caching, retry loops, generic wrappers, or event buses "just in case". Solve only the immediate problem in front of you.
- **Delete Weightless Code**: Prefer removing code over adding it. The best code is no code.

### 3. Surgical, Minimal Diffs
- **Touch Only the Essential**: Modify only the lines and symbols strictly necessary to fulfill the request.
- **Zero Drive-By Refactors**: Do not reformat untouched functions, do not rename unrelated variables, and do not reorganize imports unless directly broken.
- **Preserve Existing Style**: Match the local convention of the surrounding file perfectly, even if it differs from your personal ideal.

### 4. Empirical, Goal-Driven Verification
- **"If you didn't execute it, it's probably broken"**: Never assert that code works, compiles, or passes tests based on intuition.
- **Narrowest Reproducer**: Reproduce bugs with the smallest reproducible test or throwaway script before and after fixing.
- **Check Compiler / Linter Output**: Run real build checks (`cargo check`, `./gradlew compileDebugKotlin`, `dart analyze`). Inspect error codes and logs directly.

---

## Karpathy Failure-Mode Checklist

Before finalizing any non-trivial implementation, run this checklist:

- [ ] **No Hallucinated APIs**: Did I verify that every imported function/method actually exists in the installed library version?
- [ ] **No Drive-By Changes**: Is every changed line in the `git diff` directly linked to the user's request?
- [ ] **Simplest Viable Approach**: Could this have been implemented in fewer lines without introducing new classes or abstractions?
- [ ] **Empirical Proof**: Did I run the command, test, or check that proves this change actually works at runtime?
