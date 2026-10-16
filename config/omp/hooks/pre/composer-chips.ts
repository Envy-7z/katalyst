import type { ExtensionAPI } from "@oh-my-pi/pi-coding-agent";
import { execSync } from "child_process";
import { homedir } from "os";
import { join } from "path";

/**
 * Composer Action Chips & Slash Commands (Windsurf / Orca pattern):
 * Registers /fix-ci, /jira, /mobile, /diff, and /search commands for instant access.
 */
export default function composerChipsExtension(pi: ExtensionAPI): void {
  const localBin = join(homedir(), ".local", "bin");
  const execEnv = { ...process.env, PATH: `${localBin}:${process.env.PATH || ""}` };

  // 1. /fix-ci command
  pi.registerCommand("fix-ci", {
    description: "Inspect failed GitHub Actions CI checks and auto-generate fix prompt",
    handler: async (args: string, ctx) => {
      ctx.ui.notify("Inspecting broken CI checks...", "info");
      try {
        const cmd = `katalyst-fix-ci ${args || ""}`;
        const output = execSync(cmd, { env: execEnv, encoding: "utf-8", timeout: 30000 }).trim();
        pi.sendUserMessage(output);
      } catch (err: any) {
        ctx.ui.notify(`Failed to fetch CI checks: ${err.message || String(err)}`, "error");
      }
    },
  });

  // 2. /jira command
  pi.registerCommand("jira", {
    description: "Fetch Jira ticket summary & AC and format implementation prompt (e.g. /jira GBS-5164)",
    handler: async (args: string, ctx) => {
      const issueKey = (args || "").trim();
      if (!issueKey) {
        ctx.ui.notify("Please specify Jira issue key (e.g. /jira GBS-5164)", "warning");
        return;
      }
      ctx.ui.notify(`Fetching Jira issue ${issueKey}...`, "info");
      try {
        const cmd = `katalyst-jira ${issueKey}`;
        const output = execSync(cmd, { env: execEnv, encoding: "utf-8", timeout: 20000 }).trim();
        pi.sendUserMessage(output);
      } catch (err: any) {
        ctx.ui.notify(`Failed to fetch Jira ticket: ${err.message || String(err)}`, "error");
      }
    },
  });

  // 3. /mobile command
  pi.registerCommand("mobile", {
    description: "List mobile devices, emulators, or reverse ports (e.g. /mobile devices, /mobile reverse)",
    handler: async (args: string, ctx) => {
      const sub = (args || "").trim() || "devices";
      try {
        const output = execSync(`katalyst-mobile ${sub}`, { env: execEnv, encoding: "utf-8", timeout: 15000 }).trim();
        pi.sendUserMessage(`### Mobile Status:\n\`\`\`text\n${output}\n\`\`\``);
      } catch (err: any) {
        ctx.ui.notify(`katalyst-mobile error: ${err.message || String(err)}`, "error");
      }
    },
  });
  // 4. /mb command (Memory Bank manager)
  pi.registerCommand("mb", {
    description: "Manage persistent project memory bank (e.g. /mb status, /mb update, /mb plan)",
    handler: async (args: string, ctx) => {
      const sub = (args || "").trim() || "status";
      ctx.ui.notify(`Running memory bank: ${sub}...`, "info");
      try {
        const output = execSync(`memory-bank ${sub}`, { env: execEnv, encoding: "utf-8", timeout: 20000 }).trim();
        pi.sendUserMessage(output || `Memory Bank command '${sub}' executed successfully.`);
      } catch (err: any) {
        ctx.ui.notify(`Memory Bank error: ${err.message || String(err)}`, "error");
      }
    },
  });

  // 5. /start command (Load memory bank context in new session)
  pi.registerCommand("start", {
    description: "Load project status, checklist, and roadmap from .memory-bank/ into context",
    handler: async (_args: string, ctx) => {
      ctx.ui.notify("Restoring active project context from Memory Bank...", "info");
      try {
        const cmd = "source ~/.katalyst/lib/skill-memory-bank/scripts/_lib.sh && BANK=$(mb_resolve_path) && [ -d \"$BANK\" ] && cat \"$BANK/status.md\" 2>/dev/null";
        const output = execSync(cmd, { shell: "/bin/bash", env: execEnv, encoding: "utf-8", timeout: 10000 }).trim();
        if (output) {
          pi.sendUserMessage(`### 🧠 Restored Project Memory:\n${output}\n\n*Siap lanjut tugas berikutnya, apa yang mau kita kerjakan?*`);
        } else {
          pi.sendUserMessage("*(Belum ada .memory-bank/ di project ini. Ketik `/mb init` untuk membuat memory bank baru)*");
        }
      } catch (err: any) {
        ctx.ui.notify(`Failed to load memory bank: ${err.message || String(err)}`, "warning");
      }
    },
  });

  // 6. /done command (Complete task and save delta to memory bank)
  pi.registerCommand("done", {
    description: "Complete current task, update checklist, and record progress in .memory-bank/",
    handler: async (args: string, ctx) => {
      ctx.ui.notify("Finalizing task in Memory Bank...", "info");
      try {
        const note = (args || "").trim() || "Completed active task";
        const cmd = `source ~/.katalyst/lib/skill-memory-bank/scripts/_lib.sh && BANK=$(mb_resolve_path) && [ -d "$BANK" ] && echo "- [x] ${note} ($(date '+%Y-%m-%d %H:%M'))" >> "$BANK/progress.md" && echo "Progress recorded."`;
        const output = execSync(cmd, { shell: "/bin/bash", env: execEnv, encoding: "utf-8", timeout: 10000 }).trim();
        pi.sendUserMessage(`✅ **Task Finalized**: ${note}\n${output}`);
      } catch (err: any) {
        ctx.ui.notify(`Failed to update memory bank: ${err.message || String(err)}`, "error");
      }
    },
  });
}
