import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";
import { execSync } from "child_process";
import { existsSync, readFileSync } from "fs";
import { homedir } from "os";
import { join } from "path";

/**
 * Dynamic Context Hook.
 *
 * Runs on `before_agent_start` and injects one hidden custom message with:
 * 1. Deterministic skill routing (word-boundary keyword match → SKILL.md body).
 * 2. Memory-bank status on the first user turn of a session.
 * 3. @diff / @git-log / @mb / @context expansion.
 *
 * `context` handlers may only return `{ messages }`; a `systemPrompt` field there is
 * ignored by omp, which is why this lives on `before_agent_start` instead.
 */

type SkillRoute = { pattern: RegExp; skills: string[] };

// Generic routes. Project/company-specific routes live in ~/.katalyst/skill-routes.json
// ([{ "pattern": "regex", "skills": ["name"] }]) and are checked first, so domain skills
// win when more than MAX_SKILLS match.
const GENERIC_ROUTES: SkillRoute[] = [
  { pattern: /\b(security|keamanan|xss|csrf|sql\s*injection|vulnerab\w*|celah\s+keamanan)\b/, skills: ["security-best-practices", "security-and-hardening"] },
  { pattern: /\b(unit\s*tests?|bikin\s+test|tambah\s+test|tdd)\b/, skills: ["unit-test-craft", "test-driven-development"] },
  {
    pattern: /\b(ui|ux|tampilan|desain|design|frontend|css|layout|warna|landing\s?page|thumbnail|figma|tailwind)\b/,
    skills: ["antislop-ui", "boutique-ui-design"],
  },
  {
    pattern: /\b(fiverr|gig|upwork|proposal|copywriting|caption|cover\s?letter|linkedin|bio)\b/,
    skills: ["human-voice", "antislop-copywriting"],
  },
  {
    pattern: /\b(bug|error|exception|crash|force\s?close|gagal|failed|failing|stack\s?trace|timeout)\b/,
    skills: ["fault-localization", "systematic-debugging"],
  },
  { pattern: /\b(push|commit|pull\s?request|merge|rebase|cherry-pick)\b/, skills: ["git-safe-change-control"] },
  { pattern: /\b(refactor|refaktor|simplify|cleanup)\b/, skills: ["code-simplification", "safe-refactor-guard"] },
  { pattern: /\b(fix|benerin|perbaiki|implement\w*|bikin\s+fitur|tambah\s+fitur)\b/, skills: ["verification-before-completion"] },
];

const SKILL_CHAR_LIMIT = 2500;
const MAX_SKILLS = 5;
const USER_ROUTES_FILE = join(homedir(), ".katalyst", "skill-routes.json");
const MB_STATUS_CMD =
  'source ~/.katalyst/lib/skill-memory-bank/scripts/_lib.sh && BANK=$(mb_resolve_path) && [ -d "$BANK" ] && cat "$BANK/status.md" 2>/dev/null';

function loadUserRoutes(): SkillRoute[] {
  if (!existsSync(USER_ROUTES_FILE)) return [];
  try {
    const raw: unknown = JSON.parse(readFileSync(USER_ROUTES_FILE, "utf-8"));
    if (!Array.isArray(raw)) return [];
    return raw.flatMap((r): SkillRoute[] => {
      if (!r || typeof r !== "object" || !("pattern" in r) || !("skills" in r)) return [];
      const { pattern, skills } = r;
      if (typeof pattern !== "string" || !Array.isArray(skills)) return [];
      return [{ pattern: new RegExp(pattern, "i"), skills: skills.filter((s): s is string => typeof s === "string") }];
    });
  } catch {
    return []; // a broken routes file must not break prompting
  }
}

export function routeSkills(prompt: string): { names: string[]; bodies: string[] } {
  const lower = prompt.toLowerCase();
  const names: string[] = [];
  const bodies: string[] = [];
  for (const route of [...loadUserRoutes(), ...GENERIC_ROUTES]) {
    if (!route.pattern.test(lower)) continue;
    for (const name of route.skills) {
      if (names.includes(name) || names.length >= MAX_SKILLS) continue;
      const skillPath = join(homedir(), ".katalyst", "skills", name, "SKILL.md");
      if (!existsSync(skillPath)) continue;
      let raw: string;
      try {
        raw = readFileSync(skillPath, "utf-8");
      } catch {
        continue;
      }
      // A skill is claimed active only when its body was actually injected.
      names.push(name);
      const body = raw.length > SKILL_CHAR_LIMIT
        ? `${raw.slice(0, SKILL_CHAR_LIMIT)}\n[truncated; read skill://${name} for the rest]`
        : raw;
      bodies.push(`#### Skill [${name}]\n${body}`);
    }
  }
  return { names, bodies };
}

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

    // 1. Skill routing
    const { names, bodies } = routeSkills(prompt);
    if (names.length > 0) {
      const activeLine = ["token-saving", "caveman-lite", ...names].join(", ");
      sections.push(
        [
          "### Auto-routed skills",
          `These skill bodies are loaded for this turn: ${names.join(", ")}.`,
          `Start your reply with exactly: \`Active skills: ${activeLine}\` and apply these skills.`,
          ...bodies,
        ].join("\n\n"),
      );
    }

    // 2. Memory bank on first turn (or explicit @mb / @context)
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

    // 3. @diff / @git-log
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
        details: { skills: names },
      },
    };
  });
}
