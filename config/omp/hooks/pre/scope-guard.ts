import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";
import { homedir } from "os";
import { dirname, isAbsolute, resolve, sep } from "path";

/**
 * Scope Guard: blocks off-task exploration that prompt rules alone did not stop
 * (observed with Gemini Flash): process inspection, other sessions' transcripts,
 * sibling/parent directories, shell history, account enumeration, and decoding
 * secret files. Each block is lifted when the latest user prompt asks for it.
 */

type Verdict = { block: true; reason: string } | undefined;

const SECRET_FILE = /(^|[\s/'"])(\.env(\.[\w-]+)?|[\w.-]*\.(pem|key|p12)|id_(rsa|ed25519)|credentials(\.json)?)\b/i;

const BASH_RULES: Array<{ cmd: RegExp; unlock: RegExp; reason: string }> = [
  {
    cmd: /(^|[;&|(]|\$\()\s*(sudo\s+)?(ps|lsof|pgrep|pkill|kill|killall|top|htop)(\s|$)/,
    unlock: /\b(ps|proses|process|pid|lsof|port|kill|matiin|jalan(nya)?\s+apa)\b/i,
    reason: "Process inspection/killing is off-task unless the user asks about processes.",
  },
  {
    cmd: /\bgh\s+(repo\s+list|api\s+(user|users|orgs)\b)/,
    unlock: /\b(repo(s|sitori)?\s+(list|gw|saya|lu)|daftar\s+repo|github\s+(account|akun))\b/i,
    reason: "Enumerating the user's GitHub account is off-task unless asked.",
  },
  {
    cmd: /(_history\b|(^|[;&|\s])history(\s|$)|fc\s+-l)/,
    unlock: /\b(history|riwayat\s+(command|terminal|shell))\b/i,
    reason: "Shell history is private and off-task unless the user asks for it.",
  },
];

function bashVerdict(command: string, prompt: string): Verdict {
  if (/\b(base64|xxd|od|hexdump|strings)\b/.test(command) && SECRET_FILE.test(command)) {
    return { block: true, reason: "Decoding a secret file is never allowed. Tell the user to view it locally (e.g. `cat .env`)." };
  }
  for (const rule of BASH_RULES) {
    if (rule.cmd.test(command) && !rule.unlock.test(prompt)) return { block: true, reason: rule.reason };
  }
  return undefined;
}

function pathsOf(input: Record<string, unknown>): string[] {
  const raw = [input.path, input.paths, input.cwd].flatMap((v) => (Array.isArray(v) ? v : [v]));
  return raw
    .filter((v): v is string => typeof v === "string" && v.length > 0)
    .flatMap((v) => v.split(";"))
    .map((v) => v.trim())
    .filter((v) => v && !/^[a-z]+:\/\//i.test(v)) // skill://, omp://, https:// …
    .map((v) => v.replace(/:(raw|conflicts|img|[-\d,+:]+)(:raw)?$/, "")); // strip read selectors
}

function expand(p: string, cwd: string): string {
  const home = p === "~" || p.startsWith("~/") ? homedir() + p.slice(1) : p;
  return isAbsolute(home) ? resolve(home) : resolve(cwd, home);
}

function within(child: string, parent: string): boolean {
  return child === parent || child.startsWith(parent.endsWith(sep) ? parent : parent + sep);
}

function pathVerdict(paths: string[], cwd: string, prompt: string): Verdict {
  const parent = dirname(cwd);
  const guardSiblings = cwd !== homedir() && parent !== "/" && parent !== homedir();
  for (const p of paths) {
    const abs = expand(p, cwd);
    const named = prompt.includes(p) || prompt.includes(abs);
    if (abs.endsWith(".jsonl") && !within(abs, cwd) && !named
      && !/\b(jsonl|transcript|session|sesi|thread|log|history|riwayat)\b/i.test(prompt)) {
      return { block: true, reason: `Reading another session/transcript (${p}) is off-task unless the user names it.` };
    }
    if (guardSiblings && !named && within(abs, parent) && !within(abs, cwd)) {
      return { block: true, reason: `${p} is outside the working directory (${cwd}). Only touch paths the user named.` };
    }
  }
  return undefined;
}

const FAST_MODEL = /(flash|haiku|mini|luna|nano|lite)/i;
const BIG_REFACTOR = /\b(refactor|refaktor|rapikan|rewrite|migrasi|ganti\s+semua)\b/i;
const MANY_FILES = /\b(semua|seluruh|sekaligus|all)\b|\b(ke-?)?\s*([4-9]|\d{2,})\s+file/i;
const CONTINUE_ANYWAY = /\b(lanjut(in)?|tetap|tetep|gas(\s+aja)?|pakai\s+model\s+ini|ga\s*usah\s+ganti\s+model|continue)\b/i;
const EDIT_TOOLS: Record<string, true> = { edit: true, write: true, ast_edit: true };

/** Fast models must hand multi-file refactors to a stronger model unless the user insists. */
export function escalationVerdict(modelId: string, toolName: string, prompt: string): Verdict {
  if (!EDIT_TOOLS[toolName] || !FAST_MODEL.test(modelId)) return undefined;
  if (!BIG_REFACTOR.test(prompt) || !MANY_FILES.test(prompt) || CONTINUE_ANYWAY.test(prompt)) return undefined;
  return {
    block: true,
    reason: `Multi-file refactor on fast model ${modelId}: do not edit yet. Tell the user to switch with \`/model\` to Opus or Sonnet, and only continue on this model if they reply "lanjut".`,
  };
}

export function checkScope(toolName: string, input: Record<string, unknown>, cwd: string, prompt: string): Verdict {
  if (toolName === "bash" || toolName === "eval") {
    const code = typeof input.command === "string" ? input.command : typeof input.code === "string" ? input.code : "";
    const v = bashVerdict(code, prompt);
    if (v) return v;
  }
  if (["read", "grep", "glob", "edit", "write", "ast_grep", "ast_edit"].includes(toolName)) {
    return pathVerdict(pathsOf(input), cwd, prompt);
  }
  return undefined;
}

function field(value: unknown, key: string): unknown {
  return value !== null && typeof value === "object" && key in value
    ? (value as Record<string, unknown>)[key]
    : undefined;
}

function sessionKey(ctx: unknown): string {
  const sm = field(ctx, "sessionManager");
  const get = field(sm, "getSessionId");
  try {
    return typeof get === "function" ? String(get.call(sm)) : "default";
  } catch {
    return "default";
  }
}

export default function scopeGuard(pi: HookAPI): void {
  const prompts = new Map<string, string>();

  pi.on("before_agent_start", async (event, ctx) => {
    const p = field(event, "prompt");
    if (typeof p === "string") prompts.set(sessionKey(ctx), p);
  });

  pi.on("tool_call", async (event, ctx) => {
    const name = field(event, "toolName");
    const input = field(event, "input");
    if (typeof name !== "string" || !input || typeof input !== "object") return;
    const rawCwd = field(ctx, "cwd");
    const cwd = typeof rawCwd === "string" && rawCwd ? rawCwd : process.cwd();
    const prompt = prompts.get(sessionKey(ctx)) ?? "";
    const models = field(ctx, "models");
    const current = field(models, "current");
    let modelId = "";
    try {
      const m: unknown = typeof current === "function" ? current.call(models) : undefined;
      const id = field(m, "id");
      modelId = typeof id === "string" ? id : "";
    } catch {
      modelId = "";
    }
    const verdict = escalationVerdict(modelId, name, prompt) ?? checkScope(name, input as Record<string, unknown>, cwd, prompt);
    if (verdict) return { block: true, reason: `[scope-guard] ${verdict.reason}` };
  });

  pi.on("session_shutdown", async (_event, ctx) => {
    prompts.delete(sessionKey(ctx));
  });
}
