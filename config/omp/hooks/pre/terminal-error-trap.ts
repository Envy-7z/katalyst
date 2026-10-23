import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";

/**
 * Terminal Error Trap Hook:
 * On a failed bash tool result, appends a diagnostic instruction to the tool result
 * content so the model cannot treat a broken command as success.
 *
 * `tool_result` handlers may return `{ content }`; a `systemPrompt` field is ignored.
 */
type TextBlock = { type: "text"; text: string };

function isTextBlock(block: unknown): block is TextBlock {
  return block !== null && typeof block === "object" && "type" in block && block.type === "text"
    && "text" in block && typeof block.text === "string";
}

export default function terminalErrorTrapHook(pi: HookAPI): void {
  pi.on("tool_result", async (event) => {
    if (!event || typeof event !== "object") return;
    const toolName = "toolName" in event ? event.toolName : undefined;
    if (toolName !== "bash") return;

    const content = "content" in event && Array.isArray(event.content) ? event.content : [];
    const text = content.filter(isTextBlock).map((b) => b.text).join("\n");
    const exitMatch = text.match(/Command exited with code (\d+)/i) || text.match(/exit status (\d+)/i);
    const isError = "isError" in event && event.isError === true;
    if (!isError && !(exitMatch && exitMatch[1] !== "0")) return;

    const exitCode = exitMatch ? exitMatch[1] : "unknown";
    const trap: TextBlock = {
      type: "text",
      text: [
        "",
        `[terminal-error-trap] This command FAILED (exit code: ${exitCode}).`,
        "Diagnose the root cause from the output above before running more commands.",
        "Do not report this step as successful.",
      ].join("\n"),
    };
    return { content: [...content, trap] };
  });
}
