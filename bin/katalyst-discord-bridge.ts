#!/usr/bin/env -S node --experimental-strip-types
/**
 * Katalyst v0.3.0 Ultra-Lightweight Discord Remote Bridge
 * Full Remote Control: Projects, Threads, Execution, and Prompts
 * Security: Strict Author ID whitelist
 */

import { execSync, spawn } from "node:child_process";
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

interface DiscordConfig {
  enabled?: boolean;
  bot_token?: string;
  channel_id?: string;
  webhook_url?: string;
  authorized_user_ids?: string[];
}

function loadConfig(): DiscordConfig {
  const configPath = join(homedir(), ".config/zed/settings.json");
  if (!existsSync(configPath)) return {};
  try {
    const raw = JSON.parse(readFileSync(configPath, "utf-8"));
    return raw["katalyst.discord"] || {};
  } catch {
    return {};
  }
}

const config = loadConfig();

if (!config.enabled && !process.env.DISCORD_BOT_TOKEN) {
  console.log("[katalyst-discord-bridge] Discord integration is disabled in settings.json. Exiting.");
  process.exit(0);
}

const token = process.env.DISCORD_BOT_TOKEN || config.bot_token;
const channelId = process.env.DISCORD_CHANNEL_ID || config.channel_id;
const authorizedUsers = new Set(config.authorized_user_ids || []);

if (!token || !channelId) {
  console.log("[katalyst-discord-bridge] Missing token or channel_id. Exiting.");
  process.exit(0);
}

const ALLOWED_SLASH_COMMANDS = new Set([
  "/help",
  "/commands",
  "/projects",
  "/open",
  "/threads",
  "/thread",
  "/models",
  "/model",
  "/status",
  "/approve",
  "/continue",
  "/abort",
]);

interface ModelInfo {
  id: string;
  name: string;
  tag: string;
}

const POPULAR_MODELS: ModelInfo[] = [
  { id: "openai-codex/gpt-5.6-luna", name: "GPT-5.6-Luna (OpenAI Codex - Default)", tag: "luna" },
  { id: "google-antigravity/gemini-3.8-flash", name: "Gemini 3.8 Flash (Super Cepat & Kuota Jumbo)", tag: "gemini" },
  { id: "google-antigravity/gemini-2.5-pro", name: "Gemini 2.5 Pro (Deep Reasoning)", tag: "gemini-pro" },
  { id: "google-antigravity/claude-sonnet-4-6", name: "Claude Sonnet 4.6 (High Precision)", tag: "sonnet" },
  { id: "google-antigravity/claude-opus-4-6", name: "Claude Opus 4.6 (Heavy Logic)", tag: "opus" },
];

let selectedModel = (config as any).model || "openai-codex/gpt-5.6-luna";

function updateSettingsModel(modelId: string) {
  const configPath = join(homedir(), ".config/zed/settings.json");
  if (!existsSync(configPath)) return;
  try {
    const raw = JSON.parse(readFileSync(configPath, "utf-8"));
    if (raw.agent_servers && raw.agent_servers.omp) {
      if (!raw.agent_servers.omp.default_config_options) {
        raw.agent_servers.omp.default_config_options = {};
      }
      raw.agent_servers.omp.default_config_options.model = modelId;
      writeFileSync(configPath, JSON.stringify(raw, null, 2));
    }
  } catch {}
}

interface ThreadInfo {
  session_id: string;
  title: string;
}

let activeThread: ThreadInfo | null = null;
let activeJob: any = null;

function isAuthorized(userId: string): boolean {
  return authorizedUsers.has(userId);
}

function getRecentThreads(): ThreadInfo[] {
  const dbPath = join(homedir(), "Library/Application Support/Zed/db/0-dev/db.sqlite");
  if (!existsSync(dbPath)) return [];
  try {
    const query = "SELECT session_id, title FROM sidebar_threads WHERE archived = 0 AND title != '' ORDER BY updated_at DESC LIMIT 6;";
    const output = execSync(`/usr/bin/sqlite3 -readonly "${dbPath}" "${query}"`, { encoding: "utf-8" });
    const list: ThreadInfo[] = [];
    for (const line of output.split("\n")) {
      const parts = line.split("|");
      if (parts.length >= 2 && parts[0] && parts[1]) {
        list.push({ session_id: parts[0].trim(), title: parts[1].trim() });
      }
    }
    return list;
  } catch {
    return [];
  }
}

function getAvailableProjects(): { name: string; path: string }[] {
  const base = join(homedir(), "Documents/Projects");
  if (!existsSync(base)) return [];
  const results: { name: string; path: string }[] = [];
  try {
    const entries = readdirSync(base, { withFileTypes: true });
    for (const ent of entries) {
      if (ent.isDirectory() && !ent.name.startsWith(".") && ent.name !== "__MACOSX") {
        if (ent.name === "bitbucket") {
          const bitbucketDir = join(base, "bitbucket");
          const sub = readdirSync(bitbucketDir, { withFileTypes: true });
          for (const s of sub) {
            if (s.isDirectory() && !s.name.startsWith(".")) {
              results.push({ name: `bitbucket/${s.name}`, path: join(bitbucketDir, s.name) });
            }
          }
        } else {
          results.push({ name: ent.name, path: join(base, ent.name) });
        }
      }
    }
  } catch {}
  return results.slice(0, 20);
}

function findSessionFile(sessionId: string): string | null {
  const base = join(homedir(), ".omp/agent/sessions");
  if (!existsSync(base)) return null;
async function handleAttachments(attachments: any[]): Promise<string[]> {
  if (!attachments || attachments.length === 0) return [];
  const cacheDir = join(homedir(), ".katalyst/cache/discord-attachments");
  if (!existsSync(cacheDir)) {
    execSync(`mkdir -p "${cacheDir}"`);
  }
  const downloaded: string[] = [];
  for (const att of attachments) {
    try {
      const filename = att.filename || `file_${Date.now()}`;
      const localPath = join(cacheDir, `${Date.now()}_${filename}`);
      const res = await fetch(att.url);
      const buffer = Buffer.from(await res.arrayBuffer());
      writeFileSync(localPath, buffer);
      downloaded.push(localPath);
    } catch (err) {
      console.error("[katalyst-discord-bridge] Failed to download attachment:", err);
    }
  }
  return downloaded;
}


  try {
    const out = execSync(`/usr/bin/find "${base}" -type f -name "*${sessionId}*.jsonl" | head -n 1`, { encoding: "utf-8" }).trim();
    return out || null;
  } catch {
    return null;
  }
}

async function sendDiscordMessage(chId: string, payload: { content?: string; embeds?: any[] }) {
  try {
    const res = await fetch(`https://discord.com/api/v10/channels/${chId}/messages`, {
      method: "POST",
      headers: {
        Authorization: `Bot ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      console.error("[katalyst-discord-bridge] Send failed:", res.status, await res.text());
    }
  } catch (err) {
    console.error("[katalyst-discord-bridge] Network error sending message:", err);
  }
}

// Connect to Discord Gateway WebSocket
let heartbeatInterval = 41250;
let lastSequence: number | null = null;
let ws: WebSocket | null = null;
let heartbeatTimer: any = null;

function connectGateway() {
  try {
    ws = new WebSocket("wss://gateway.discord.gg/?v=10&encoding=json");

    ws.onopen = () => {
      console.log("[katalyst-discord-bridge] Connected to Discord Gateway WebSocket.");
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data.toString());
        const { op, d, s, t } = payload;
        if (s !== null) lastSequence = s;

        switch (op) {
          case 10: // Hello
            heartbeatInterval = d.heartbeat_interval;
            startHeartbeat();
            identify();
            break;
          case 11: // Heartbeat ACK
            break;
          case 0: // Dispatch
            handleDispatch(t, d);
            break;
          case 7: // Reconnect
          case 9: // Invalid Session
            reconnect();
            break;
        }
      } catch (err) {
        console.error("[katalyst-discord-bridge] Message parse error:", err);
      }
    };

    ws.onerror = (err) => {
      console.error("[katalyst-discord-bridge] WebSocket error:", err);
    };

    ws.onclose = () => {
      console.log("[katalyst-discord-bridge] Gateway closed. Reconnecting in 5s...");
      clearInterval(heartbeatTimer);
      setTimeout(connectGateway, 5000);
    };
  } catch (err) {
    console.error("[katalyst-discord-bridge] Connection error:", err);
    setTimeout(connectGateway, 10000);
  }
}

function startHeartbeat() {
  clearInterval(heartbeatTimer);
  heartbeatTimer = setInterval(() => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ op: 1, d: lastSequence }));
    }
  }, heartbeatInterval);
}

function identify() {
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(
      JSON.stringify({
        op: 2,
        d: {
          token,
          intents: (1 << 9) | (1 << 15), // GUILD_MESSAGES | MESSAGE_CONTENT
          properties: {
            os: "darwin",
            browser: "katalyst",
            device: "katalyst",
          },
        },
      })
    );
  }
}

function reconnect() {
  if (ws) ws.close();
}

async function handleDispatch(eventType: string, data: any) {
  if (eventType === "MESSAGE_CREATE") {
    // Ignore bot messages or messages outside target channel
    if (data.author.bot || data.channel_id !== channelId) return;

    // Strict security check: verify user ID
    if (!isAuthorized(data.author.id)) {
      console.warn(`[katalyst-discord-bridge] Blocked message from unauthorized user ID: ${data.author.id} (${data.author.username})`);
      await sendDiscordMessage(channelId, {
        content: `⛔ **Akses Ditolak.** Perangkat ini diproteksi dan hanya menerima perintah dari akun owner. (User ID kamu: \`${data.author.id}\`)`,
      });
      return;
    }

    const rawText = (data.content || "").trim();
    if (!rawText) return;

    // Command handling
    if (rawText.startsWith("/")) {
      const parts = rawText.split(" ");
      const cmd = parts[0].toLowerCase();

      if (!ALLOWED_SLASH_COMMANDS.has(cmd)) {
        await sendDiscordMessage(channelId, {
          content: `⚠️ Perintah \`${cmd}\` tidak dikenali. Ketik \`/help\` untuk melihat daftar perintah yang tersedia.`,
        });
        return;
      }

      if (cmd === "/help" || cmd === "/commands") {
        await sendDiscordMessage(channelId, {
          embeds: [
            {
              title: "⚡ Katalyst Remote Control — Bantuan Perintah",
              description:
                "Gunakan perintah ini untuk mengendalikan Mac & Katalyst kamu secara penuh dari Discord:",
              fields: [
                { name: "📁 `/projects`", value: "Menampilkan daftar project di Mac kamu (`~/Documents/Projects/`)." },
                { name: "📂 `/open <nomor/nama>`", value: "Membuka window project tersebut langsung di aplikasi Katalyst." },
                { name: "📋 `/threads`", value: "Menampilkan daftar thread agent yang sedang aktif di sidebar." },
                { name: "🎯 `/thread <nomor/nama>`", value: "Memilih thread target yang ingin kamu ajak chat / beri perintah." },
                { name: "🤖 `/models`", value: "Melihat daftar model AI yang tersedia (GPT-5.6, Gemini 3.8, Claude, dll)." },
                { name: "🔄 `/model <nomor/nama>`", value: "Mengganti model AI secara instan saat kehabisan kuota (contoh: `/model 2` atau `/model gemini`)." },
                { name: "📊 `/status`", value: "Melihat status koneksi bridge, thread terpilih, dan kondisi Mac kamu." },
                { name: "✅ `/approve`", value: "Menyetujui review plan agent dan memulai eksekusi (`/go`)." },
                { name: "▶️ `/continue`", value: "Meneruskan eksekusi bila agent menunggu input." },
                { name: "🛑 `/abort`", value: "Membatalkan / menghentikan task agent yang sedang berjalan." },
                { name: "💬 Kirim Chat Langsung", value: "Ketik teks biasa apa saja (tanpa `/`) untuk langsung menyuruh agent ngoding di thread terpilih!" },
              ],
              color: 0x3b82f6,
              footer: { text: "Security: Whitelist Protected (Owner Only)" },
            },
          ],
        });
        return;
      }

      if (cmd === "/projects") {
        const projects = getAvailableProjects();
        if (projects.length === 0) {
          await sendDiscordMessage(channelId, { content: "📁 Tidak ada folder project yang ditemukan di `~/Documents/Projects/`." });
          return;
        }
        let text = "📁 **Daftar Project di Mac Kamu (`~/Documents/Projects/`):**\n\n";
        projects.forEach((p, i) => {
          text += `\`${i + 1}.\` **${p.name}**\n`;
        });
        text += `\nKetik \`/open <nomor>\` atau \`/open <nama>\` untuk membuka project di Katalyst (contoh: \`/open 1\`).`;
        await sendDiscordMessage(channelId, { content: text });
        return;
      }

      if (cmd === "/open") {
        const target = parts.slice(1).join(" ").trim();
        if (!target) {
          await sendDiscordMessage(channelId, { content: "⚠️ Masukkan nomor atau nama project. Contoh: `/open 1` atau ketik `/projects` untuk melihat daftar." });
          return;
        }
        const projects = getAvailableProjects();
        let found: { name: string; path: string } | undefined;
        const num = parseInt(target, 10);
        if (!isNaN(num) && num >= 1 && num <= projects.length) {
          found = projects[num - 1];
        } else {
          found = projects.find((p) => p.name.toLowerCase().includes(target.toLowerCase()));
        }

        if (!found) {
          await sendDiscordMessage(channelId, {
            content: `❌ Project \`${target}\` tidak ditemukan. Ketik \`/projects\` untuk melihat daftar folder yang ada.`,
          });
          return;
        }

        try {
          execSync(`open -a /Applications/Katalyst.app "${found.path}"`);
          await sendDiscordMessage(channelId, {
            content: `📂 **Project Berhasil Dibuka!**\nWindow **${found.name}** sekarang sudah terbuka di Katalyst Mac kamu.\n\`Path: ${found.path}\``,
          });
        } catch (err: any) {
          await sendDiscordMessage(channelId, { content: `❌ Gagal membuka project: ${err.message}` });
        }
        return;
      }

      if (cmd === "/threads") {
        const threads = getRecentThreads();
        if (threads.length === 0) {
          await sendDiscordMessage(channelId, { content: "📋 Tidak ada thread aktif yang ditemukan di Katalyst." });
          return;
        }
        let text = "📋 **Daftar Thread Aktif di Katalyst:**\n\n";
        threads.forEach((t, i) => {
          const isCurr = activeThread && activeThread.session_id === t.session_id;
          text += `\`${i + 1}.\` ${isCurr ? "👉 **[Aktif]** " : ""}**${t.title}**\n   \`ID: ${t.session_id.slice(0, 18)}...\`\n`;
        });
        text += `\nKetik \`/thread <nomor>\` untuk berpindah thread (contoh: \`/thread 1\`).`;
        await sendDiscordMessage(channelId, { content: text });
        return;
      }

      if (cmd === "/thread") {
        const target = parts.slice(1).join(" ").trim();
        if (!target) {
          await sendDiscordMessage(channelId, { content: "⚠️ Masukkan nomor atau nama thread. Contoh: `/thread 1` atau ketik `/threads` untuk melihat daftar." });
          return;
        }
        const threads = getRecentThreads();
        let selected: ThreadInfo | null = null;
        const num = parseInt(target, 10);
        if (!isNaN(num) && num >= 1 && num <= threads.length) {
          selected = threads[num - 1];
        } else {
          selected = threads.find((t) => t.title.toLowerCase().includes(target.toLowerCase())) || null;
        }

        if (selected) {
          activeThread = selected;
          await sendDiscordMessage(channelId, {
            content: `🎯 **Thread Terpilih:** **${selected.title}**\n\`Session ID: ${selected.session_id}\`\nSemua perintah dan chat sekarang diarahkan ke thread ini!`,
          });
        } else {
          await sendDiscordMessage(channelId, {
            content: `❌ Thread \`${target}\` tidak ditemukan. Ketik \`/threads\` untuk melihat daftar thread yang ada.`,
          });
        }
        return;
      }
      if (cmd === "/models") {
        let text = "🤖 **Daftar Model AI yang Tersedia di Mac Kamu:**\n\n";
        POPULAR_MODELS.forEach((m, i) => {
          const isCurr = selectedModel === m.id;
          text += `\`${i + 1}.\` ${isCurr ? "👉 **[Aktif]** " : ""}**${m.name}**\n   \`ID: ${m.id}\n`;
        });
        text += `\nKetik \`/model <nomor>\` atau \`/model <nama>\` untuk mengganti model (contoh: \`/model 2\` atau \`/model gemini\`).`;
        await sendDiscordMessage(channelId, { content: text });
        return;
      }

      if (cmd === "/model") {
        const target = parts.slice(1).join(" ").trim();
        if (!target) {
          await sendDiscordMessage(channelId, {
            content: "⚠️ Masukkan nomor atau nama model. Contoh: `/model 2` atau `/model gemini`. Ketik `/models` untuk melihat daftar.",
          });
          return;
        }

        let found: ModelInfo | undefined;
        const num = parseInt(target, 10);
        if (!isNaN(num) && num >= 1 && num <= POPULAR_MODELS.length) {
          found = POPULAR_MODELS[num - 1];
        } else {
          found = POPULAR_MODELS.find(
            (m) =>
              m.id.toLowerCase().includes(target.toLowerCase()) ||
              m.name.toLowerCase().includes(target.toLowerCase()) ||
              m.tag.toLowerCase().includes(target.toLowerCase())
          );
        }

        if (found) {
          selectedModel = found.id;
          updateSettingsModel(found.id);
          await sendDiscordMessage(channelId, {
            content: `🔄 **Model Berhasil Diganti!**\n\nModel aktif sekarang: **${found.name}**\n\`ID: ${found.id}\`\n\nSemua perintah kerja selanjutnya otomatis menggunakan model ini (kuota baru aktif)! 🚀`,
          });
        } else if (target.includes("/")) {
          selectedModel = target;
          updateSettingsModel(target);
          await sendDiscordMessage(channelId, {
            content: `🔄 **Model Custom Diaktifkan:** \`${target}\`\nPengaturan telah disimpan ke Katalyst!`,
          });
        } else {
          await sendDiscordMessage(channelId, {
            content: `❌ Model \`${target}\` tidak dikenali. Ketik \`/models\` untuk melihat daftar model yang tersedia.`,
          });
        }
        return;
      }

      if (cmd === "/status") {
        const currentTitle = activeThread ? activeThread.title : "Thread Terbaru (Auto-detect)";
        let memInfo = "Normal";
        try {
          const df = execSync("df -h / | awk 'NR==2 {print $4}'", { encoding: "utf-8" }).trim();
          memInfo = `Free Disk: ${df}`;
        } catch {}

        await sendDiscordMessage(channelId, {
          embeds: [
            {
              title: "Katalyst Remote Agent Status",
              description: `🟢 **Online & Connected**\n\n**Active Model:** \`${selectedModel}\`\n**Mac Host:** Darwin arm64 (${memInfo})\n**Target Thread:** ${currentTitle}\n**Security:** Authorized (${data.author.username})\n**Engine:** Oh My Pi (ACP / Autonomous)`,
              color: 0x10b981,
              footer: { text: "Katalyst v0.3.0 · Full Remote Bridge" },
            },
          ],
        });
        return;
      }

      if (cmd === "/abort") {
        if (activeJob) {
          try {
            activeJob.kill("SIGINT");
            activeJob = null;
            await sendDiscordMessage(channelId, { content: "🛑 Task agent yang sedang berjalan berhasil dibatalkan." });
          } catch (e: any) {
            await sendDiscordMessage(channelId, { content: `⚠️ Gagal membatalkan task: ${e.message}` });
          }
        } else {
          await sendDiscordMessage(channelId, { content: "ℹ️ Tidak ada task agent yang sedang berjalan." });
        }
        return;
      }

      if (cmd === "/approve" || cmd === "/continue") {
        const threads = getRecentThreads();
        const target = activeThread || threads[0];
        if (!target) {
          await sendDiscordMessage(channelId, { content: "⚠️ Tidak ada thread aktif untuk di-approve." });
          return;
        }

        const sessFile = findSessionFile(target.session_id);
        if (!sessFile) {
          await sendDiscordMessage(channelId, { content: `❌ File session untuk thread **${target.title}** tidak ditemukan di disk.` });
          return;
        }

        const prompt = cmd === "/approve" ? "/go" : "continue";
        await sendDiscordMessage(channelId, {
          content: `⚡ Mengirim \`${prompt}\` ke thread **${target.title}**... Agent mulai mengeksekusi!`,
        });

        // Run omp in background
        // Run omp in non-interactive print mode with selected model
        const ompArgs = ["-p", "-r", sessFile];
        if (selectedModel) {
          ompArgs.push("--model", selectedModel);
        }
        ompArgs.push(prompt);
        activeJob = spawn("/opt/homebrew/bin/omp", ompArgs, {
          stdio: ["ignore", "pipe", "pipe"],
          env: { ...process.env, NO_COLOR: "1", TERM: "dumb" },
        });

        activeJob.on("close", async (code: number) => {
          activeJob = null;
          await sendDiscordMessage(channelId, {
            content: `🏁 Eksekusi \`${prompt}\` pada thread **${target.title}** selesai dengan code ${code}. Ketik pesan untuk instruksi selanjutnya!`,
          });
        });
        return;
      }
    } else {
      // Plain text message: treat as agent prompt!
      const threads = getRecentThreads();
      const target = activeThread || threads[0];
      if (!target) {
        await sendDiscordMessage(channelId, { content: "⚠️ Tidak ada thread aktif di Katalyst. Buka project dulu via `/open` atau `/threads`." });
        return;
      }

      const sessFile = findSessionFile(target.session_id);
      if (!sessFile) {
        await sendDiscordMessage(channelId, { content: `❌ Session file untuk thread **${target.title}** tidak ditemukan.` });
        return;
      }

      const files = await handleAttachments(data.attachments || []);
      let promptToSend = rawText;
      let previewMsg = rawText;
      if (files.length > 0) {
        const fileReferences = files.map((f) => `[File/Image Lampiran: ${f}]`).join("\n");
        promptToSend = `${fileReferences}\n${rawText}`.trim();
        previewMsg = `[${files.length} Lampiran File/Foto] ${rawText}`;
      }

      await sendDiscordMessage(channelId, {
        content: `📥 **Instruksi Diterima:** "${previewMsg.slice(0, 150)}${previewMsg.length > 150 ? "..." : ""}"\nTarget Thread: **${target.title}**\n⏳ *Agent di Mac kamu sedang memproses...*`,
      });

      // Dispatch to omp with -p and clean terminal output
      const ompArgs = ["-p", "-r", sessFile];
      if (selectedModel) {
        ompArgs.push("--model", selectedModel);
      }
      ompArgs.push(promptToSend);
      activeJob = spawn("/opt/homebrew/bin/omp", ompArgs, {
        stdio: ["ignore", "pipe", "pipe"],
        env: { ...process.env, NO_COLOR: "1", TERM: "dumb" },
      });

      let stdoutData = "";
      activeJob.stdout.on("data", (chunk: Buffer) => {
        stdoutData += chunk.toString();
      });

      activeJob.on("close", async (code: number) => {
        activeJob = null;
        let responsePreview = stdoutData.trim();
        // Clean up any stray ANSI escape codes
        responsePreview = responsePreview.replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, "").trim();
        if (!responsePreview) {
          responsePreview = "Agent telah selesai menjalankan instruksi.";
        }
        if (responsePreview.length > 1800) {
          responsePreview = responsePreview.slice(-1800);
        }
        await sendDiscordMessage(channelId, {
          content: `✅ **Katalyst Selesai:** (Thread: **${target.title}**)\n\n${responsePreview}`,
        });
      });
    }
  }
}

console.log("[katalyst-discord-bridge] Starting Katalyst v0.3.0 Discord Bridge...");
connectGateway();
