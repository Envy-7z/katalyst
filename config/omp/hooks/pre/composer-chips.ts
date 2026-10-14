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
}
