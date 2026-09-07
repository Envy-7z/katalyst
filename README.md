<p align="center">
  <img src="assets/logo.png" width="128" height="128" alt="Katalyst Logo" />
</p>

<h1 align="center">Katalyst ⚡</h1>

<p align="center">
  <strong>The autonomous, high-performance agentic development suite powered by Zed Editor (Rust) and OMP (Agent Client Protocol).</strong>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-GPL--3.0-blue.svg" alt="License: GPL-3.0" /></a>
  <a href="https://github.com/can1357/oh-my-pi"><img src="https://img.shields.io/badge/engine-OMP_ACP-brightgreen.svg" alt="OMP Engine" /></a>
  <a href="https://apple.com/macos"><img src="https://img.shields.io/badge/platform-macOS_%7C_Windows_(soon)-blueviolet.svg" alt="Platform: macOS | Windows (soon)" /></a>
  <a href="https://github.com/Envy-7z/katalyst/releases"><img src="https://img.shields.io/github/v/release/Envy-7z/katalyst?color=blue&label=release" alt="Release" /></a>
</p>

<p align="center">
  <img src="assets/katalyst-preview.png" width="920" alt="Katalyst Agentic IDE Preview" />
</p>

---
## 💡 What is Katalyst?

**Katalyst** is a production-ready, open-source coding environment that bridges the blazing speed of **Zed** (native GPU-accelerated Rust) with the autonomous intelligence of **OMP** via the open Agent Client Protocol (ACP).

It gives you the best of both worlds:
* **Zero Electron Bloat**: Sub-second cold starts, 60fps scrolling, minimal RAM footprint.
* **Autonomous Engineering**: Autonomous agents that plan multi-step architecture, execute terminal commands safely, run tests, and refactor code without getting stuck.

---

## ⚡ 1-Line Quickstart (macOS)

Open your terminal and paste this single command:

```bash
curl -fsSL https://raw.githubusercontent.com/Envy-7z/katalyst/main/install.sh | bash
```

> [!TIP]
> **Zero Manual Setup**: The installer automatically detects your Mac, installs OMP and Katalyst/Zed if missing, links optimized configurations, and configures 12 autonomous engineering skills.

<details>
<summary><strong>Manual Clone Option (for contributors & developers)</strong></summary>

```bash
git clone https://github.com/Envy-7z/katalyst.git ~/.katalyst
cd ~/.katalyst && ./install.sh
```
</details>
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

## ✨ Features You Won't Find in Stock Zed

| Feature | Stock Zed | Katalyst ⚡ |
|---|:---:|:---:|
| **Plan & Build Toolbar** | ❌ No | ✅ **One-click `[ ▶ Build Locally ]` on any `*.plan.md`** |
| **Model Switcher on Plan** | ❌ No | ✅ **Instant `[ Auto ˅ ]` picker in preview toolbar** |
| **Multi-Question Form Scroll** | ⚠️ Buttons get cut off | ✅ **Capped at 420px with internal smooth scrolling** |
| **Prompt Recovery on Cancel** | ❌ Prompt lost | ✅ **Canceled prompts automatically restored in composer** |
| **Answered Request Badges** | ❌ Takes up huge space | ✅ **Collapses into sleek 1-line status badges** |
| **Daily Update Notifications** | ❌ No native alert | ✅ **macOS Notification Center banner at 09:00 AM** |
| **Universal Skills Suite** | ❌ Empty | ✅ **12 pre-loaded skills (TDD, Debugging, S3, Worktrees)** |

---

## 🔑 Setting Up AI Models (3 Ways)

Katalyst supports any major cloud model or 100% free local models:

### 1. Interactive Browser Login (Recommended)
Connect your existing subscriptions with encrypted Keychain storage:

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

To update OMP and pull the latest upstream patches:

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

## 📄 License & Credits

* Katalyst modifications and tooling are distributed under the **GNU General Public License v3.0 (GPL-3.0)**.
* Core editor architecture copyright © [Zed Industries, Inc.](https://zed.dev)
* Agent runtime powered by [OMP](https://github.com/can1357/oh-my-pi).
* Created with ❤️ by [Wisnuu](https://github.com/Envy-7z).
