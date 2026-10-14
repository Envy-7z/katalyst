import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";

/**
 * Intelligent Context Condenser Hook:
 * Optimizes token retention during session auto-compaction and prevents 500k context bloat.
 */
export default function sessionCompaction(pi: HookAPI): void {
  pi.on("session.compacting", async (_event: Record<string, unknown>) => {
    return {
      prompt: [
        "Summarize this session into dense, actionable sections:",
        "",
        "## Decisions & Constraints",
        "- Architectural, schema, and API decisions with rationale.",
        "- User preferences and standing invariants.",
        "",
        "## Files Modified & Created",
        "- Exact file paths and what changed in each (bullet format).",
        "",
        "## Active State & Pending Tasks",
        "- Specific TODO items and their progress (done vs remaining).",
        "- Unresolved bugs, active error stack traces, and verification status.",
        "",
        "## Critical Context Anchors",
        "- Active git branch name.",
        "- Key symbol names, API paths, and configuration keys.",
        "",
        "CRITICAL INSTRUCTION: Completely discard raw tool dumps (terminal logs, full file bodies,",
        "git status noise, grep output). Preserve ONLY distilled conclusions and exact symbols.",
      ].join("\n"),
      context: [
        "Preserve active branch names and uncommitted edit paths.",
        "Preserve exact error messages and verification results.",
        "Preserve discovered patterns and user language preferences.",
      ],
    };
  });

  // Ensure auto-compaction proceeds naturally without cancellation
  pi.on("session_before_compact", async (_event: Record<string, unknown>) => {
    return { cancel: false };
  });
}
