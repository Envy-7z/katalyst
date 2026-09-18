<p align="center">
  <img src="assets/logo.png" width="128" height="128" alt="Katalyst Logo" />
</p>

<h1 align="center">Katalyst ⚡</h1>

<p align="center">
  <strong>The autonomous, calm, and lightning-fast developer environment — combining native GPU-accelerated Rust with fearless agentic engineering.</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue.svg" alt="License: GPL-3.0" /></a>
  <a href="https://github.com/can1357/oh-my-pi"><img src="https://img.shields.io/badge/engine-OMP_ACP-brightgreen.svg" alt="OMP Engine" /></a>
  <a href="https://apple.com/macos"><img src="https://img.shields.io/badge/platform-macOS_%7C_Windows_(soon)-blueviolet.svg" alt="Platform: macOS | Windows (soon)" /></a>
  <a href="https://github.com/Envy-7z/katalyst/releases"><img src="https://img.shields.io/github/v/release/Envy-7z/katalyst?color=blue&label=release" alt="Release" /></a>
</p>

<p align="center">
  <img src="assets/katalyst-preview.png" width="920" alt="Katalyst autonomous workspace with plan review and agent execution" />
</p>

---
## 💡 What is Katalyst?
**Katalyst** is a production-ready, open-source agentic IDE built on native GPU-accelerated Rust (GPUI) and powered by **OMP** through the open Agent Client Protocol (ACP).

It gives you the best of both worlds:
* **Zero Electron Bloat**: Sub-second cold starts, 120fps fluid scrolling, minimal ~250MB RAM footprint.
* **Autonomous Engineering**: Intelligent agents that plan multi-step architecture, execute terminal commands safely, run tests, and refactor code fearlessly.
* **Calm, Native & Predictable**: Governed by our [25 Non-Negotiable Product Principles](PRINCIPLES.md) — prioritizing stability, low memory, zero UI blocking, and quiet focus over decorative AI widgets.
---

## 🧭 Architecture & Product Principles

Katalyst is engineered under strict architectural constraints. Every patch, feature, and workflow must pass the **[25 Non-Negotiable Product Principles](PRINCIPLES.md)**:

> **STABILITY > PERFORMANCE > UX POLISH > FEATURES**  
> *"Katalyst disappears and lets me code."*

Read the full charter: **[`PRINCIPLES.md`](PRINCIPLES.md)**.
---

## ⚡ 1-Line Quickstart (macOS)

Open your terminal and paste this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/Envy-7z/katalyst/main/install.sh | bash
```

> [!TIP]
> **Apple Silicon (M1/M2/M3/M4)**: Supported out-of-the-box via prebuilt release assets with zero manual setup.  
> **Intel Mac (x86_64)**: Prebuilt binary packaging is currently pending in CI. Intel Mac users can install immediately using the **Manual Clone Option** below.
<details>
<summary><strong>Manual Clone Option (for contributors & developers)</strong></summary>

```bash
git clone https://github.com/Envy-7z/katalyst.git ~/Developer/katalyst-source
cd ~/Developer/katalyst-source && ./install.sh
```
</details>
---

## 🔄 Bring Your Cursor and Codex Chats

Katalyst imports local Cursor and Codex transcripts into resumable OMP sessions. Source files remain read-only, repeated syncs do not duplicate sessions, and a chat is never overwritten after you continue it in OMP.

```bash
# Preview what Katalyst detects
katalyst-session-sync sync --sources cursor,codex --dry-run --json

# Import all detected chats
katalyst-session-sync sync --sources cursor,codex --all --json

# Show current counts and sync ownership
katalyst-session-sync status --json
```

The installer runs the first import and registers a macOS LaunchAgent that watches Cursor and Codex session directories, with a five-minute fallback interval. Import state and provenance live at `~/.katalyst/imports/session-sync.json`.

### v0.3.x Desktop UI & Autonomous Superpowers

Katalyst v0.3.0 introduces developer superpower workflow parity with Cursor and Codex, combined with native GPU-accelerated Rust performance:

![Katalyst v0.3.x workspace](assets/katalyst-preview.png)

Key enhancements in v0.3.0:
- **Right-Panel Plan Preview & Action Toolbar**: Creating or planning tasks (`*.plan.md`) automatically opens a rendered markdown preview to the right (`SplitDirection::Right`) with interactive action buttons: `[ Approve & Execute ]`, `[ Build Locally ]`, and `[ Edit in Buffer ]`.
- **Permanent Thread Deletion**: Right-click any thread in the sidebar or click the hover trash icon to permanently remove it from both SQLite metadata and unlinked session transcripts.
- **Two-Way Discord Remote Bridge (`katalyst-discord-bridge`)**: Ultra-lightweight Bun/Node daemon (<15MB RAM, 0% idle CPU) streaming rich embeds to Discord and accepting remote prompt replies/approvals from mobile.
- **In-Buffer Visual Diff Review Strip**: Floating action bar anchored to `AgentDiffPane` (`[ ↩ Revert Turn (⌥⌘Z) ]` `[ ✎ Edit in Buffer ]` `[ ✓ Keep All (Enter) ]`) with zero cursor jitter.
- **Process Group Reaper**: Automatic `SIGTERM` followed by 2s grace period before `SIGKILL` on shutdown, guaranteeing zero orphaned OMP processes.
- **Sidebar Categorization & Source Badges**: Threads organized by `Today`, `Previous 7 Days`, and `Older` with visual source tags (`[Cursor]`, `[Codex]`, `[OMP]`).
- **Standalone Release-Fast Packaging**: Compiled with `profile.release-fast`, reducing disk footprint from 1.17 GB to 450 MB with 0.079s instant startup.
### Privacy boundary

The repository contains generic defaults, example MCP configuration, release scripts, and reusable skills. Personal Cursor/Codex rules, hooks, settings, MCP credentials, raw transcripts, and provider accounts stay on the local machine under `~/.katalyst/private-profile` and are never copied into this repository. The installer migrates compatible local skills and MCP definitions without publishing the source files or secrets.

---

## 🧠 Architecture Overview

```text
┌────────────────────────────────────────────────────────┐
│                   KATALYST SUITE                       │
│                                                        │
│  ┌───────────────────────┐   ACP (RPC)  ┌───────────┐  │
│  │      Zed Editor       │ ◄──────────► │    OMP    │  │
│  │   (Native Rust UI)    │              │  (Engine) │  │
│  └──────────┬────────────┘              └─────┬─────┘  │
│             │                                 │        │
│    ┌────────┴────────┐               ┌────────┴──────┐ │
│    │  Custom Patches │               │ Core Skills   │ │
│    │  • Plan Toolbar │               │ • TDD & Debug │ │
│    │  • Form Scroll  │               │ • Refactoring │ │
│    │  • Recovery     │               │ • Worktrees   │ │
│    └─────────────────┘               └───────────────┘ │
└───────────────────────────────────────────────┼────────┘
                                                ▼
                                    Claude / GPT / Ollama
```

---

## ⚡ The Katalyst Advantage: Native Speed Meets Autonomous Power

| Capability | Conventional AI IDEs (Electron) | Stock Text Editors | Katalyst ⚡ |
|---|:---:|:---:|:---:|
| **Engine & Runtime Speed** | 2–4 GB RAM, Chromium micro-stutters | ~200 MB RAM, fast but no AI agents | **~250 MB RAM, Native GPU-Accelerated Rust (120 FPS)** |
| **Autonomous Multi-Step Planning** | Unstructured chat or background loops | None | **Interactive `*.plan.md` with 1-click `[ ▶ Build Locally ]` & phase tracking** |
| **Working Copy Safety** | Overwrite risk, destructive rollbacks | Manual git stash | **Lossless Git Checkpoint Revert (`⌥⌘Z`) preserving uncommitted work** |
| **Crash Protection** | Leaves dirty or broken files | None | **Automatic pre-turn snapshot rollback on agent crash** |
| **Diff Review & Co-Editing** | Webview diffs, separate modal popups | Read-only split buffers | **Bi-Directional MultiBuffer Co-Editing (`Type to edit · Enter to keep`)** |
| **Interface Tranquility** | Cluttered glowing frames & tall cards | None | **Calm Conversation UI (Compact 24px chips with exit status badges)** |
| **Privacy & Secret Guard** | Leaks uncommitted `.env` to models | None | **Pre-prompt Shannon entropy scanner ($H > 4.5$) auto-scrubbing credentials** |
| **Large Workspace Scalability** | Heavy recursive indexing freezes IDE | Locks on git operations | **Zero-wait prompt dispatch, shallow scan caps, 60s timeout & auto resume fallback** |
| **Lifecycle & Crash Immunity** | Silent background exits, unhandled panics | None | **AppKit auto-termination immunity, bounds-checked parsing, seamless session recovery** |
| **Session Portability** | Locked in proprietary formats | None | **1-click lossless import from Cursor and Codex transcripts** |
| **Anti-Sleep Streaming** | Mac sleeps mid-task, aborting agents | None | **Display sleep assertion keeps background agent execution alive** |
| **Turn Step Numbering** | Flat unnumbered stream | None | **Sequential `Step X/Y` badges on tool execution cards** |
| **Elicitation Forms** | Massive persistent forms cut off buttons | None | **Scroll-capped forms that auto-collapse into clean 1-line badges** |
---

## 🔑 Setting Up AI Models (3 Ways)

Katalyst supports any major cloud model or 100% free local models:

### 1. In-App Provider Accounts GUI (Recommended)
Open **Settings (`Cmd+,`) → External Agents** to see all connected provider accounts, quotas, and status. Click **`Connect Account…`** to launch the docked in-app terminal and connect subscriptions or API keys via `/login`.

Alternatively, use the terminal directly:
```bash
# For Claude 3.7 Sonnet / Opus
omp auth-broker login anthropic

# For GPT-4o / o1 / o3
omp auth-broker login openai

# For GitHub Copilot
omp auth-broker login github-copilot

# For Google Gemini
omp auth-broker login google-antigravity
```

### 2. Standard API Keys via Shell
Add to your `~/.zshrc` or `~/.bashrc`:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="AIza..."
```
Then run: `source ~/.zshrc`.

### 3. 100% Free & Offline (Ollama)
Run models locally with zero subscriptions and zero data leaving your machine:

```bash
brew install ollama && brew services start ollama
ollama run qwen2.5-coder
```
Katalyst automatically detects and routes prompts to local Ollama instances.

---

## 🧑‍💻 The First 5 Minutes: Daily Workflow

### Step 1: Open Your Project
```bash
# Open any project folder
open -a Katalyst ~/projects/my-web-app
# Or using terminal command
zed ~/projects/my-web-app
```

### Step 2: Open the Agent Panel
Press **`Cmd + Shift + A`** to toggle the agent sidebar.

### Step 3: Architecture-First Planning
Instead of asking for messy blind edits, prompt the agent to create a plan:

```text
/plan Add user authentication with JWT, refresh token rotation, and unit tests
```

### Step 4: One-Click Execution
1. Katalyst will generate a structured plan file (`~/.katalyst/plans/<slug>.plan.md`).
2. The file automatically opens in the editor pane with full formatting.
3. Look at the top-right toolbar:
   * Select your model: **`[ Auto ˅ ]`**
   * Click **`[ ▶ Build Locally ]`**
4. The agent executes the plan systematically, verifying each checkpoint.

---

## ⌨️ Essential Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Cmd + Shift + A` | Toggle Agent Panel |
| `Cmd + \` | Toggle Bottom Terminal Dock |
| `Cmd + P` | Fast File Finder |
| `Cmd + Shift + P` | Command Palette |
| `Escape` (while generating) | Stop generation & restore prompt into composer |

---
## 💰 Token Cost & Telemetry (`omp-cost`)

Katalyst integrates natively with **`omp-cost`** to track multi-profile AI spend, prompt cache hit ratios, and per-model consumption directly from your local session database:

```bash
# Run quick cost report across all profiles
omp-cost

# Filter by specific profile or time window
omp-cost --profile default --period 7d
```

* **Cache Savings Visibility**: Real-time insight into prompt-cache efficiency (typically 85%–91% cost reduction).
* **Multi-Account Tracking**: Accurate breakdown across Google Antigravity, Copilot, Codex, and Anthropic.

---


## 🧩 Extending Katalyst: Skills, MCP Servers & Hooks

Katalyst is designed to be fully extensible. You can easily teach your agent new domain knowledge, connect external tools, and intercept execution lifecycles.

---

### 1. 🧠 Adding Custom Skills

Skills give your agent specialized expertise (e.g., specific framework conventions, testing rules, design systems).

* **Global location**: `~/.katalyst/skills/<skill-name>/SKILL.md` (available across all projects).
* **Project location**: `.agents/skills/<skill-name>/SKILL.md` (inside any specific repository).

To create a new skill, create a folder and add a `SKILL.md` file with standard frontmatter:

```markdown
---
name: nextjs-app-router
description: Conventions for Next.js App Router, Server Components, and Server Actions. Trigger when editing pages, layouts, or data mutations in Next.js projects.
---

# Next.js App Router Conventions

## Rules
1. Prefer React Server Components by default; only add `'use client'` when interactive state (e.g., `useState`, `useEffect`) is strictly required.
2. Colocate Server Actions in `actions.ts` or inline with `'use server'`.
3. Handle async errors using `error.tsx` boundary files.

## Verification
Run `npm run build` or `npm run typecheck` to verify changes before completing.
```

> [!NOTE]
> **Zero Restart Required**: Katalyst auto-discovers newly created skills on the fly.

---

### 2. 🔌 Adding MCP Servers (Model Context Protocol)

MCP allows the agent to interact with databases, web browsers, API docs, and third-party services. Configure them in `~/.omp/agent/mcp.json`:

```json
{
  "mcpServers": {
    "playwright": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "context7": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "context7-mcp@latest"]
    },
    "postgres": {
      "type": "stdio",
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-postgres",
        "postgresql://user:password@localhost:5432/mydb"
      ]
    },
    "sqlite": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "app.db"]
    },
    "openaiDocs": {
      "type": "http",
      "url": "https://developers.openai.com/mcp"
    }
  }
}
```

Restart Katalyst (`open -a Katalyst`) to load new MCP servers.

---

### 3. 🪝 Adding Lifecycle Hooks

Hooks allow you to intercept and control agent actions before or after they execute:

* **Pre-Execution Hooks** (`~/.omp/agent/hooks/pre/`): Run before a tool executes. Can block, gate, or ask for user confirmation on dangerous actions.
* **Post-Execution Hooks** (`~/.omp/agent/hooks/post/`): Run after a tool finishes. Ideal for automated formatting (Prettier, Biome), auditing, or telemetry.

#### Example: Safety Gate Hook (`~/.omp/agent/hooks/pre/gate-dangerous.ts`)

```typescript
// Gate dangerous pipe-to-shell or destructive deletions
export default async function (action: { tool: string; params: any }) {
  if (action.tool === "bash") {
    const cmd = action.params?.command || "";
    if (cmd.match(/rm\s+-rf\s+(\/|~|\$HOME)/) || cmd.match(/\|\s*(sudo\s+)?(bash|sh|zsh)/)) {
      return {
        allow: false,
        reason: "Blocked potentially destructive command. User confirmation required."
      };
    }
  }
  return { allow: true };
}
```
---

## 🗺️ Platform Support & Roadmap

* 🍏 **macOS (Apple Silicon & Intel)**: **Full Support (Production Ready)** — Available via 1-line curl installer and pre-built binaries on [GitHub Releases](https://github.com/Envy-7z/katalyst/releases).
* 🪟 **Windows (x64 / ARM64)**: **In Development (Roadmap)** — GitHub Actions CI compilation pipeline in progress.
* 🐧 **Linux (x64)**: **Planned** — Native Wayland/X11 build target.

---

## 🛠️ Keeping Katalyst Updated

To install the latest signed or ad-hoc signed Katalyst release and update OMP:

```bash
katalyst-update
```

Every morning at 09:00 AM, a gentle macOS notification banner will also let you know if any new updates are available.

---

## ❓ Troubleshooting & FAQ

<details>
<summary><strong>How do I change the default AI model?</strong></summary>

Open `~/.config/zed/settings.json` and change:
```json
"default_model": {
  "provider": "zed.dev",
  "model": "claude-sonnet-4-6"
}
```
Or switch models dynamically inside the Agent Panel dropdown or toolbar picker.
</details>

<details>
<summary><strong>Can I use my existing VSCode keybindings?</strong></summary>

Yes! Katalyst comes with `"base_keymap": "VSCode"` enabled by default, so all standard shortcuts feel immediately familiar.
</details>

<details>
<summary><strong>Where are my skills located?</strong></summary>

All skills are stored in `~/.katalyst/skills/`. You can add custom `.md` skills anytime and the agent will automatically discover them.
</details>
---

## 💬 Feedback, Feature Requests & Community

Katalyst is an evolving, community-driven project. We'd love to hear your thoughts, ideas, and feedback!

* 💡 **Feature Requests & Ideas**: Have an idea for a new agent skill, workflow, or tool integration? Open an issue on [GitHub Issues](https://github.com/Envy-7z/katalyst/issues).
* 🐛 **Bug Reports**: Encountered an issue with installation or UI? Submit a bug report via [GitHub Issues](https://github.com/Envy-7z/katalyst/issues).
* 🤝 **Feedback & collaboration**: Open an issue or discussion in the [Katalyst repository](https://github.com/Envy-7z/katalyst).
* ⭐ **Support the Project**: If Katalyst speeds up your development workflow, consider giving the repository a star on GitHub!

---

## 📄 License & Credits

* Katalyst modifications and tooling are distributed under the **GNU General Public License v3.0 (GPL-3.0)**.
* Core editor architecture copyright © [Zed Industries, Inc.](https://zed.dev)
* Agent runtime powered by [OMP](https://github.com/can1357/oh-my-pi).
* Maintained by Katalyst Contributors.

---

## Privacy and local profile migration

Katalyst's repository contains only generic defaults, public documentation, and the patch series needed to build the app. It does not include a user's credentials, chat transcripts, private skills, rules, commands, hooks, or machine paths.

During installation, `katalyst-migrate-profile` copies the current machine's Cursor and Codex setup into `~/.katalyst`:

- User skills are copied into Katalyst's local skill directory and are available to OMP.
- Compatible MCP server definitions are merged into `~/.omp/agent/mcp.json`; an existing OMP definition wins if names collide.
- Cursor rules, commands, hooks, and Codex configuration/hooks are retained under `~/.katalyst/private-profile/` as local provenance. They are not published and are not auto-enabled across agent runtimes because their event formats differ.
- The installer preserves the existing Zed settings, keymap, OMP configuration, and MCP file before applying Katalyst defaults.

This keeps personal workflow automation on the user's Mac while allowing the public release to remain reproducible and safe to share.

## Updating upstream Zed and OMP

Katalyst keeps the upstream Zed revision in [`ZED_REVISION`](ZED_REVISION) and applies the numbered patch series during every release build. To update, start from a clean worktree, move the pinned revision forward, apply the patch series, resolve conflicts, run the test suite, and release a new Katalyst version.

OMP remains an external dependency installed through its official package channel. Updating OMP does not replace the Katalyst runtime, and Katalyst preserves the user's local OMP configuration and profile migration data across upgrades.
