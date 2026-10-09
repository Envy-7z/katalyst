# Katalyst History and Workflow Upgrade Plan

**Goal:** Make imported history chronological and safe, reduce avoidable workflow friction, and update the live Katalyst/OMP installation without losing active sessions or local changes.

**Architecture:** Keep OMP transcripts as source of truth. Fix the Cursor/Codex importer and ACP history metadata at the source; do not rewrite OMP-owned transcripts. Treat Google Chat as an optional, explicit QA handoff, not an agent-end notification. Update Zed by rebuilding the pinned patched source against a verified upstream revision only if all 52 patches and runtime checks work.

**Stack:** Python 3 importer, Rust/GPUI Zed fork, OMP ACP, macOS launchd, GitHub Actions.

## Constraints and baseline

- Preserve five pre-existing uncommitted Discord/Mac-status files in the original `katalyst` checkout; this plan and new work are on `fix/history-workflow-20261010` in a separate worktree.
- Existing `/Applications/Katalyst.app` and two OMP ACP processes are running. Never replace the app binary or restart those processes mid-turn.
- Current source pin is `ZED_REVISION=1a84d5d92bd7d6c1cabb116062650af545783fe9`; the old root Zed clone is missing, leaving child worktrees with broken Git pointers. Reconstruct from upstream in a new directory, not by overwriting them.
- Baseline suite: 32/33 passing. `test_audit_privacy_script_passes` fails only because its audit includes the isolated worktree's `.git` pointer containing a local path. Fix and test the audit before committing.
- Importer reports 82 sources, 75 OMP-owned sessions and one malformed legacy projection (`OMP transcript has no session record`). Preserve the malformed file; never auto-delete or rewrite OMP-owned history.

## Slice 1 — Import reliability and chronology

**Files:** `tests/test_session_sync.py`, `lib/katalyst_session_sync.py`, `tests/test_privacy_guard.py`, `scripts/audit-privacy.sh`.

1. Write regressions with synthetic Cursor transcripts: embedded `<timestamp>` in message text, timestamp fallback when absent, and an OMP-owned legacy target missing a `session` header. Assert source-accurate ascending message times, stable import filename, no rewrite of owned targets, visible warning rather than repeated fatal daemon exit. Write an isolated-worktree privacy audit regression.
2. Verify failing tests: `python3 -m unittest tests/test_session_sync.py tests/test_privacy_guard.py -v` (or `python3 -m unittest discover -s tests -v` if namespace import differs). Distinguish expected RED from the known audit baseline failure.
3. Implement only metadata parsing, safe skip of malformed owned projection, and `.git` exclusion in the audit script. Preserve importer state/target idempotence. Re-run targeted tests and full unittest suite. Smoke using `katalyst-session-sync sync --sources cursor,codex --all --dry-run --json`, then install only the verified importer script/wrapper and check automatic launch agent once.

## Slice 2 — ACP sidebar ordering and Zed upstream evaluation

**Files:** patched Zed `crates/agent_servers/src/acp.rs`, `crates/agent_ui/src/thread_import.rs`, related existing Rust tests, new patch `patches/0053-*.patch`, `ZED_REVISION` only if rebased, release config tests.

1. Reconstruct a clean pinned Zed source outside the broken worktrees with upstream clone and apply patch series. Validate current app's behavior and metadata preservation with a focused regression before editing.
2. Check Zed v1.23.2 ACP thread/status changes against Katalyst patches. Either port a small independently useful fix or rebase the entire patch series **only if** conflict resolution is bounded, tests pass, and build resources permit. Do not relabel current source as updated without a build. ACP `session/list` timestamps must not default historical imports to now.
3. Run Rust targeted tests and `cargo check -p agent_ui -p agent_servers`; build the actual app bundle, sign it after stopping the app cleanly, launch, open an imported historical thread, and confirm its position and content. If a safe local GUI build is impossible, do not replace the installed app; expose the precise blocker and preserve the working app.

## Slice 3 — Lean workflow and optional QA handoff

**Files:** `README.md`, `config/omp/mcp.json.example`, existing workflow documentation; implementation file only if a concrete local trigger with real verification exists.

1. Document the task ladder: small fixes use OMP plan mode only when useful, cross-session work uses the existing Katalyst `.plan.md` review; separate worktrees for independently writable agent tasks; one integration gate; self-test + deploy verification before QA notification.
2. Keep the 23 locally configured MCP servers intact unless usage evidence supports removal. Prefer on-demand existing tools to adding new servers or duplicating 16 packaged skills. Protect local employer-specific skill/config data from the public repo.
3. For the screenshots' ticket/branch/environment/test cases, add a manually invoked QA handoff template/checklist using verified facts. Do not auto-send on `agent_end`; Google Chat incoming webhook is optional, one-way, space-specific, and requires a user-provided secret. No webhook URL is present or to be committed. Require deployment verification and deduplicate sends if a real sender is later adopted.

## Slice 4 — OMP and release/deployment safety

**Files:** `bin/katalyst-update`, `tests/test_installer.py`/release tests, `CHANGELOG.md`, `README.md`; local OMP binary and Katalyst app only after verification.

1. Test mismatch: runtime VERSION=0.3.0, repo=0.3.2, GitHub latest=0.3.1 must never cause an unintended downgrade. Fix version detection/guard; avoid coupling an app reinstall to an OMP update.
2. Upgrade OMP from 18.4.2 to a pinned published release after backup of user-owned config, ensuring running ACP sessions are not killed. Verify new CLI version, model discovery and a fresh ACP smoke without changing the current session.
3. Full tests, privacy audit, shell syntax, patch applicability and runtime smoke. Stage explicit allowlisted files, inspect diff for credentials/internal company text, commit and push only the new branch to the user's GitHub repository; do not include unrelated dirty changes.
4. Deploy only a built and validated Mac app via backup/atomic replacement when the app is not running; check code signature, startup, ACP connection, imported history and rollback path. Report any block truthfully; never claim upstream Zed/app updated merely because source or OMP changed.

## Sources and decisions

- Zed: https://github.com/zed-industries/zed/releases/tag/v1.23.2
- OMP: https://github.com/can1357/oh-my-pi/releases/tag/v18.8.7
- Orca (worktree per task, terminal/diff): https://www.onorca.dev/docs
- Google Chat incoming webhook limitations: https://developers.google.com/workspace/chat/quickstart/webhooks

**Deliberate non-goals:** no new MCP server; no Discord replacement daemon; no automatic Jira transitions, deploys or Google Chat posts; no rewriting 75 OMP-owned imported sessions; no copying private company workflows into public GitHub.