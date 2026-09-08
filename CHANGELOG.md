# Changelog

All notable changes to the **Katalyst** project (custom Zed fork optimized for autonomous agent workflows, ACP, and mobile development) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.3] - 2026-09-08

### Added
- **Inline Review Plan Card**:
  - Assistant message turns proposing or referencing a plan now render an inline `ReviewPlanCard` with plan title, 2-line summary, `Open Plan` and one-click `Build Locally` button.
- **Phase Ratio Progress Chip (`2/6`)**:
  - Activity bar plan summary now renders a fraction chip (`x/total · y left`) during execution, providing live step progress.
- **Active Skills Metadata Pill**:
  - Renders an explicit styled badge (`IconName::Sparkle` + pill) when an assistant message announces active skills.
- **Subagent Card Step Indicator**:
  - Collapsed subagent card headers now display step counts when no file diffs are present.

---

## [0.1.2] - 2026-09-08

### Added
- **Plan checklist progress (Modern-style)**:
  - Auto-seed ACP execution plan from `*.plan.md` on Build Locally or `/go <path>`.
  - Parses Approach phases and marks items InProgress/Completed as turns finish or checkboxes flip.
- **Context meter idle placeholder**:
  - Displays muted `Context —` chip with helpful tooltip when agent omits `UsageUpdate`.
- **In-app Connect Account**:
  - Connect Account opens an interactive `omp` shell directly inside the docked TerminalPanel.

---

## [0.1.1] - 2026-09-08

### Added
- **OMP Provider Accounts (GUI)**:
  - Settings → External Agents now shows connected OMP provider accounts (identity + latest usage status).
  - **Connect Account…** opens Terminal with OMP and prompts `/login` — no CLI scavenger hunt for friends/onboarding.

### Fixed
- Plan toolbar accepts both `*.plan.md` and `*-plan.md`; Build + model selector remain visible in Markdown Preview tabs (patch 0013).
- Plan auto-open hook strips accidental `nan#` prefixes when mirroring plans; propose-resilience guidance added to agent rules.

### Changed
- About dialog version bumped to **Katalyst 0.1.1**.

---

## [0.1.0] - 2026-09-08

### Added
- **Modern Autonomous Agent Sidebar**:
  - Prominent **"New chat"** action row at the top of the sidebar with dedicated compose icon, label, plus badge, and tooltip.
  - **"Projects"** collapsible section header with an inline `+` ("Add Folder to Project…") action that launches the native directory picker to add local directories/workspaces to the sidebar.
  - Repository-based accordions with project names, active status badges, and cleanly nested threads.
  - **Pinned Section**: Persistent SQLite-backed thread pinning (`pinned` column in `thread_metadata`) with always-visible muted pin badges.
  - **"No Repo" Fallback Section**: Dedicated section for threads created without an associated workspace or folder.
  - **Filter-Time Visual Accordion Expansion**: When searching threads, matching entries under collapsed project headers are visually revealed without mutating the user's persisted collapsed/expanded state.
- **Native Plan Mode & "Build Locally" Toolbar**:
  - Quick action toolbar on all `*.plan.md` files with model selector dropdown and native `▶ Build Locally` button.
  - One-click trigger from review plan straight into agent execution (`/go`).
- **Brand Identity & App Assets**:
  - Rebranded application name to **Katalyst** across macOS app menus, About dialog, and title bars.
  - Custom Katalyst app icons (`assets/Katalyst.icns`) and logo assets rendered in the About modal.
  - Updated Welcome screens and Help menu links.

### Fixed
- **Worktree Single-File Pollution Bug**:
  - Filtered out `is_single_file()` worktrees from `get_open_folders` in `recent_projects.rs` so individual files (like `*.plan.md`) never appear as folders in the project switcher.
  - Implemented auto-purge on sidebar update to detach accidental single-file worktrees from workspaces containing real directories.
  - Prevented single-file paths from creating project group headers in the sidebar.
- **Markdown Preview Blank Race Condition**:
  - Decoupled markdown document preview rendering from pending editor layout and selection mapping. Newly opened plans render immediately rather than failing silently with an empty grey panel.
- **Header Button Redundancy**:
  - Removed duplicate `+` button from the search threads bar, keeping the search header focused and clean.
- **OMP Agent `ENOTDIR` Configuration Resolution**:
  - Replaced `zed -a` with `zed <file>` across all plan auto-open hooks and command templates, preventing OMP from binding its workspace context to a single file path.

### Changed
- **Safe Build & System Stability**:
  - Throttled build compilation concurrency to `-j2` and enforced an 8GB free disk space check in `scripts/safe-rebuild.sh` to prevent macOS memory starvation and kernel hangs during compilation.
  - Added `scripts/sync-and-rebuild.sh` for safe upstream rebasing without losing custom Katalyst features.

---

## [Unreleased]
- SQLite FTS5 full-text search integration for thread history.
- Multi-repo cross-workspace search filters.
