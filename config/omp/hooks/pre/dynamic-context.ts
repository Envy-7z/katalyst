import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";
import { execSync } from "child_process";

/**
 * Dynamic Context Hook:
 * Expands @diff, @terminal, and @git-log tokens in user prompts into real workspace state.
 */
export default function dynamicContextHook(pi: HookAPI): void {
  pi.on("context", async (event: Record<string, unknown>) => {
    const cwd = typeof event.cwd === "string" ? event.cwd : process.cwd();
    const messages = Array.isArray(event.messages) ? event.messages : [];
    if (messages.length === 0) return {};

    const lastMessage = messages[messages.length - 1];
    if (lastMessage?.role !== "user") return {};

    let userText = "";
    if (typeof lastMessage.content === "string") {
      userText = lastMessage.content;
    } else if (Array.isArray(lastMessage.content)) {
      userText = lastMessage.content
        .filter((c: any) => c.type === "text" && typeof c.text === "string")
        .map((c: any) => c.text)
        .join("\n");
    }

    const hasMentions = userText.includes("@diff") || userText.includes("@terminal") || userText.includes("@git-log") || userText.includes("@mb") || userText.includes("@context");
    if (!hasMentions) {
      return {};
    }

    const contextAdditions: string[] = [];

    // 1. @diff: Inject unstaged and staged git changes
    if (userText.includes("@diff")) {
      try {
        const diff = execSync("git diff HEAD 2>/dev/null || git diff 2>/dev/null", {
          cwd,
          timeout: 5000,
          encoding: "utf-8",
        }).trim();
        if (diff) {
          const truncated = diff.length > 8000 ? diff.slice(0, 7900) + "\n... [diff truncated]" : diff;
          contextAdditions.push("### Active @diff Context:\n```diff\n" + truncated + "\n```");
        } else {
          contextAdditions.push("### Active @diff Context:\n*(Clean working tree - no uncommitted changes)*");
        }
      } catch {
        contextAdditions.push("### Active @diff Context:\n*(Could not capture git diff)*");
      }
    }

    // 2. @git-log: Inject recent 5 commits
    if (userText.includes("@git-log")) {
      try {
        const log = execSync("git log -n 5 --oneline 2>/dev/null", {
          cwd,
          timeout: 3000,
          encoding: "utf-8",
        }).trim();
        if (log) {
          contextAdditions.push("### Recent @git-log Context:\n```\n" + log + "\n```");
        }
      } catch {
        contextAdditions.push("### Recent @git-log Context:\n*(No git history available)*");
      }
    }

    // 3. @mb or @context: Inject active project status from .memory-bank/
    if (userText.includes("@mb") || userText.includes("@context")) {
      try {
        const statusCmd = "source ~/.katalyst/lib/skill-memory-bank/scripts/_lib.sh && BANK=$(mb_resolve_path) && [ -d \"$BANK\" ] && cat \"$BANK/status.md\" 2>/dev/null";
        const mbStatus = execSync(statusCmd, { cwd, shell: "/bin/bash", timeout: 4000, encoding: "utf-8" }).trim();
        if (mbStatus) {
          const truncated = mbStatus.length > 3000 ? mbStatus.slice(0, 2900) + "\n... [memory-bank truncated]" : mbStatus;
          contextAdditions.push("### Active @mb Project Status:\n" + truncated);
        } else {
          contextAdditions.push("### Active @mb Context:\n*(No active .memory-bank found for this project)*");
        }
      } catch {
        contextAdditions.push("### Active @mb Context:\n*(Could not resolve memory bank)*");
      }
    }

    if (contextAdditions.length === 0) return {};

    return {
      systemPrompt: [
        "## Dynamic Context Expansion (@mentions)",
        ...contextAdditions,
      ].join("\n\n"),
    };
  });
}
