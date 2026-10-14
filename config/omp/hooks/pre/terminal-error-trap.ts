import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";

/**
 * Terminal Error Trap Hook (Windsurf Cascade pattern):
 * Captures non-zero shell tool exits and injects diagnostic guardrails so agents
 * never hallucinate that a broken build or failed command succeeded.
 */
export default function terminalErrorTrapHook(pi: HookAPI): void {
  pi.on("tool_result", async (event: Record<string, unknown>) => {
    const message = event.message as Record<string, unknown> | undefined;
    if (!message || message.role !== "toolResult") return;

    const toolName = message.toolName;
    if (toolName !== "bash") return;

    let contentStr = "";
    if (typeof message.content === "string") {
      contentStr = message.content;
    } else if (Array.isArray(message.content)) {
      contentStr = message.content
        .filter((c: any) => c.type === "text" && typeof c.text === "string")
        .map((c: any) => c.text)
        .join("\n");
    }

    // Detect non-zero exit code or explicit fatal error
    const exitMatch = contentStr.match(/Command exited with code (\d+)/i) || contentStr.match(/exit status (\d+)/i);
    const hasError = message.isError === true || (exitMatch && exitMatch[1] !== "0");

    if (hasError) {
      const exitCode = exitMatch ? exitMatch[1] : "unknown";
      // Extract tail of error for concise diagnostic
      const lines = contentStr.split("\n");
      const errorTail = lines.slice(-25).join("\n");

      return {
        systemPrompt: [
          "## ⚠️ Terminal Error Trap (Windsurf Cascade Guard)",
          `The last executed shell command failed (exit code: ${exitCode}).`,
          "Recent error trace:",
          "```text",
          errorTail,
          "```",
          "MANDATORY INSTRUCTION: You must diagnose the root cause of this error before running additional commands.",
          "Do not assume the build succeeded or ignore the failure.",
        ].join("\n"),
      };
    }
  });
}
