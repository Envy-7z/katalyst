import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";
import { existsSync, mkdirSync, writeFileSync } from "fs";
import { homedir } from "os";
import { dirname, isAbsolute, join, resolve } from "path";
import { execFile } from "child_process";

/**
 * Hard plan auto-open for Katalyst — current-plan only.
 *
 * Policy (user 2026-09-07):
 * - Open ONLY the *.plan.md that this tool call is actively writing.
 * - Never FS-watch ~/.cursor/plans (that reopened every plan after close).
 * - Never reopen a path already auto-opened this session (user closed = stay closed).
 * - Brand-new file create still opens once.
 */

const WRITE_TOOLS = new Set(["bash", "edit", "write", "eval", "ast_edit"]);

const HOME = homedir();

type Pending = { path: string; existedBefore: boolean };

const lastOpenedAt = new Map<string, number>();
const openedThisSession = new Set<string>();
const pendingByCall = new Map<string, Pending>();

function expandHome(p: string): string {
  if (p.startsWith("~/")) return join(HOME, p.slice(2));
  if (p.startsWith("$HOME/")) return join(HOME, p.slice(6));
  return p;
}

function normalizePlanPath(raw: string): string | null {
  let p = expandHome(raw.trim().replace(/^['"`]|['"`]$/g, ""));
  if (!p.endsWith(".plan.md")) return null;
  if (!isAbsolute(p)) p = resolve(p);
  return p;
}

/** Direct write/edit path fields only — not incidental mentions. */
function primaryWritePlanPath(
  toolName: string,
  input: Record<string, unknown>,
): string | null {
  for (const key of ["path", "file_path", "filePath"] as const) {
    const v = input[key];
    if (typeof v === "string") {
      if (v.startsWith("local://") && v.endsWith(".plan.md")) {
        const slug = v.slice(8);
        const mirrorPath = join(HOME, ".cursor/plans", slug);
        if (typeof input.content === "string") {
          try {
            mkdirSync(dirname(mirrorPath), { recursive: true });
            writeFileSync(mirrorPath, input.content, "utf-8");
          } catch {
            // non-fatal
          }
        }
        return mirrorPath;
      }
      const n = normalizePlanPath(v);
      if (n) return n;
    }
  }

  if (toolName === "bash" && typeof input.command === "string") {
    const cmd = input.command;
    const redir =
      cmd.match(
        /(?:^|[\s;|&])(?:tee(?:\s+-a)?|>{1,2})\s+((?:~|\$HOME|\/)[^\s"'`;]+\.plan\.md)/,
      ) ||
      cmd.match(
        /(?:^|[\s;|&])(?:tee(?:\s+-a)?|>{1,2})\s+['"]((?:~|\$HOME|\/)[^'"]+\.plan\.md)['"]/,
      );
    if (redir?.[1]) {
      const n = normalizePlanPath(redir[1]);
      if (n) return n;
    }
    const homeRedir = cmd.match(
      />{1,2}\s*["']?((?:\$HOME|~)\/\.cursor\/plans\/[A-Za-z0-9._-]+\.plan\.md)/,
    );
    if (homeRedir?.[1]) {
      const n = normalizePlanPath(homeRedir[1]);
      if (n) return n;
    }
  }

  if (toolName === "eval" && typeof input.code === "string") {
    const m = input.code.match(
      /(?:write|Path\([^)]*\)\s*\/)\s*['"]([^'"]+\.plan\.md)['"]|write_text\(['"]([^'"]+\.plan\.md)['"]/,
    );
    const raw = m?.[1] || m?.[2];
    if (raw) return normalizePlanPath(raw);
  }

  return null;
}

function openPlan(path: string, force: boolean): void {
  const normalized = normalizePlanPath(path);
  if (!normalized || !existsSync(normalized)) return;

  if (!force && openedThisSession.has(normalized)) {
    // User closed this tab — do not yank it open again.
    return;
  }

  const now = Date.now();
  const prev = lastOpenedAt.get(normalized) ?? 0;
  if (now - prev < 1500) return;
  lastOpenedAt.set(normalized, now);
  openedThisSession.add(normalized);

  const cliCandidates = [
    "/opt/homebrew/bin/zed",
    "/usr/local/bin/zed",
    join(HOME, ".local/bin/zed"),
    "zed",
  ];

  const tryOpen = (idx: number) => {
    if (idx >= cliCandidates.length) {
      execFile("open", ["-a", "Katalyst", normalized], { timeout: 5000 }, () => undefined);
      return;
    }
    const bin = cliCandidates[idx];
    execFile(bin, [normalized], { timeout: 5000 }, (err) => {
      if (err) tryOpen(idx + 1);
    });
  };

  try {
    mkdirSync(dirname(normalized), { recursive: true });
  } catch {
    // non-fatal
  }
  tryOpen(0);
}

export default function planAutoOpen(pi: HookAPI): void {
  pi.on("tool_call", async (event) => {
    const name = event.toolName || "";
    if (!WRITE_TOOLS.has(name)) return;

    const primary = primaryWritePlanPath(
      name,
      (event.input || {}) as Record<string, unknown>,
    );
    if (!primary) return;

    const callId =
      (event as { toolCallId?: string; id?: string }).toolCallId ||
      (event as { id?: string }).id ||
      "";

    const pending: Pending = {
      path: primary,
      existedBefore: existsSync(primary),
    };

    // Open immediately in background so pane is ready BEFORE xd://propose elicitation appears!
    openPlan(primary, true);

    if (callId) {
      pendingByCall.set(callId, pending);
      return;
    }

    setTimeout(() => {
      openPlan(pending.path, !pending.existedBefore);
    }, 400);
  });

  pi.on("tool_result", async (event) => {
    const callId =
      (event as { toolCallId?: string; id?: string }).toolCallId ||
      (event as { id?: string }).id ||
      "";
    const pending = callId ? pendingByCall.get(callId) : undefined;
    if (callId) pendingByCall.delete(callId);
    if (!pending) return;

    const isError = Boolean(
      (event as { isError?: boolean; error?: unknown }).isError ||
        (event as { error?: unknown }).error,
    );
    if (isError) return;

    // New file → force open once. Already-opened this session → stay closed.
    openPlan(pending.path, !pending.existedBefore);
  });
}
