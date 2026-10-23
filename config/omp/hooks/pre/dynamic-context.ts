import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";
import { execSync } from "child_process";

/**
 * Dynamic Context Hook.
 *
 * Runs on `before_agent_start` and injects one hidden custom message with:
 * 1. Memory-bank status on the first user turn of a session.
 * 2. @diff / @git-log / @mb / @context expansion.
 *
 * `context` handlers may only return `{ messages }`; a `systemPrompt` field there is
 * ignored by omp, which is why this lives on `before_agent_start` instead.
 */

const MB_STATUS_CMD =
  'source ~/.katalyst/lib/skill-memory-bank/scripts/_lib.sh && BANK=$(mb_resolve_path) && [ -d "$BANK" ] && cat "$BANK/status.md" 2>/dev/null';

function run(cmd: string, cwd: string, timeout: number): string {
  try {
    return execSync(cmd, { cwd, shell: "/bin/bash", timeout, encoding: "utf-8" }).trim();
  } catch {
    return "";
  }
}

function field(value: unknown, key: string): unknown {
  return value !== null && typeof value === "object" && key in value
    ? (value as Record<string, unknown>)[key]
    : undefined;
}

function isFirstUserTurn(ctx: unknown): boolean {
  const sm = field(ctx, "sessionManager");
  const getBranch = field(sm, "getBranch");
  if (typeof getBranch !== "function") return false;
  try {
    const branch: unknown = getBranch.call(sm);
    if (!Array.isArray(branch)) return false;
    return !branch.some((entry) => field(entry, "type") === "message" && field(field(entry, "message"), "role") === "user");
  } catch {
    return false;
  }
}

export default function dynamicContextHook(pi: HookAPI): void {
  pi.on("before_agent_start", async (event, ctx) => {
    const rawPrompt = field(event, "prompt");
    const prompt = typeof rawPrompt === "string" ? rawPrompt : "";
    if (!prompt) return;
    const rawCwd = field(ctx, "cwd");
    const cwd = typeof rawCwd === "string" && rawCwd ? rawCwd : process.cwd();
    const sections: string[] = [];

    // 1. Memory bank on first turn (or explicit @mb / @context)
    const wantsMb = /@mb\b|@context\b/.test(prompt);
    if (wantsMb || isFirstUserTurn(ctx)) {
      const status = run(MB_STATUS_CMD, cwd, 3000);
      if (status) {
        const body = status.length > 2500 ? `${status.slice(0, 2400)}\n[truncated]` : status;
        sections.push(`### Project memory (.memory-bank/status.md)\n${body}`);
      } else if (wantsMb) {
        sections.push("### Project memory\n(No .memory-bank found for this project.)");
      }
    }

    // 2. @diff / @git-log
    if (/@diff\b/.test(prompt)) {
      const diff = run("git diff HEAD 2>/dev/null || git diff 2>/dev/null", cwd, 5000);
      const body = !diff ? "(Clean working tree.)" : diff.length > 8000 ? `${diff.slice(0, 7900)}\n[diff truncated]` : diff;
      sections.push(`### @diff\n\`\`\`diff\n${body}\n\`\`\``);
    }
    if (/@git-log\b/.test(prompt)) {
      const log = run("git log -n 5 --oneline 2>/dev/null", cwd, 3000);
      sections.push(`### @git-log\n\`\`\`\n${log || "(No git history.)"}\n\`\`\``);
    }

    if (sections.length === 0) return;
    return {
      message: {
        customType: "katalyst.dynamic-context",
        content: sections.join("\n\n"),
        display: false,
        details: {},
      },
    };
  });
}
