import type { HookAPI } from "@oh-my-pi/pi-coding-agent/extensibility/hooks";
import { existsSync, readdirSync, readFileSync } from "fs";
import { homedir } from "os";
import { join } from "path";

/**
 * Parses simple YAML-like frontmatter without external dependencies.
 */
function parseMdcFrontmatter(content: string): { globs: string[]; body: string } {
  if (!content.startsWith("---")) {
    return { globs: [], body: content };
  }
  const end = content.indexOf("\n---", 3);
  if (end === -1) {
    return { globs: [], body: content };
  }
  const header = content.slice(3, end);
  const body = content.slice(end + 4).trim();
  const globs: string[] = [];

  for (const line of header.split("\n")) {
    const trimmed = line.trim();
    if (trimmed.startsWith("globs:")) {
      const match = trimmed.match(/globs:\s*\[(.*)\]/);
      if (match) {
        for (const item of match[1].split(",")) {
          const g = item.trim().replace(/^["']|["']$/g, "");
          if (g) globs.push(g);
        }
      }
    }
  }

  return { globs, body };
}

function matchesGlob(filename: string, globPattern: string): boolean {
  const ext = globPattern.replace(/^\*+\.?/, "");
  return filename.endsWith(ext) || filename.includes(ext);
}

/**
 * Scoped Rules Hook:
 * Dynamically loads `.katalyst/rules/*.mdc` only when matching files are present in the current turn.
 */
export default function scopedRulesHook(pi: HookAPI): void {
  pi.on("context", async (event: Record<string, unknown>) => {
    const cwd = typeof event.cwd === "string" ? event.cwd : process.cwd();
    const rulesDir = join(cwd, ".katalyst", "rules");
    if (!existsSync(rulesDir)) {
      return {};
    }

    let files: string[] = [];
    try {
      files = readdirSync(rulesDir).filter((f) => f.endsWith(".mdc") || f.endsWith(".md"));
    } catch {
      return {};
    }

    if (files.length === 0) {
      return {};
    }

    // Inspect recent turns to detect active files
    const activeText = JSON.stringify(event.messages || "");
    const activeRules: string[] = [];

    for (const file of files) {
      try {
        const fullPath = join(rulesDir, file);
        const raw = readFileSync(fullPath, "utf-8");
        const { globs, body } = parseMdcFrontmatter(raw);

        // If no globs specified, always apply
        if (globs.length === 0) {
          activeRules.push(`### Rule (${file})\n${body}`);
          continue;
        }

        // Check if any glob matches active files or extensions mentioned in context
        const matched = globs.some((g) => matchesGlob(activeText, g));
        if (matched) {
          activeRules.push(`### Scoped Rule for [${globs.join(", ")}] (${file})\n${body}`);
        }
      } catch {
        continue;
      }
    }

    if (activeRules.length === 0) {
      return {};
    }

    return {
      systemPrompt: [
        "## Active Scoped Rules (.katalyst/rules)",
        "The following context-sensitive rules apply to the matching files in this task:",
        ...activeRules,
      ].join("\n\n"),
    };
  });
}
