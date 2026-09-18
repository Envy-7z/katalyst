# 📱 Katalyst Discord Remote Control Guide

Control your **Katalyst Agent** directly from your phone or desktop via Discord when you are away from your Mac (AFK). Review and approve plans, monitor progress, open project windows, and send prompt instructions from anywhere.

---

## 🌟 What Can You Do from Discord?

* **💬 Chat & Code Remotely**: Send instructions from mobile (e.g. *"add JWT authentication with refresh token rotation and run unit tests"*). The agent on your Mac will execute commands, write code, and reply with the results in Discord.
* **✅ Approve Architecture Plans**: When an agent finishes drafting a plan (`*.plan.md`), approve it from your phone with `/approve` to start execution immediately.
* **📂 Switch Projects Remotely**: Browse your Mac's projects (`/projects`) and open any project in a Katalyst window (`/open <name>`).
* **🎯 Multi-Thread Switching**: List your active sidebar threads (`/threads`) and switch which thread you want to talk to (`/thread <number>`).
* **🛡️ Strict Whitelisting**: Only authorized Discord User IDs can send commands; all other users are blocked.

---

## 🚀 Step-by-Step Setup Walkthrough

### Step 1: Create a Discord Bot
1. Open the [Discord Developer Portal Applications page](https://discord.com/developers/applications).
2. Click **New Application** at the top right, name it (e.g., `katalyst-bot`), and click **Create**.
3. In the left sidebar, click **Bot**.
4. Under **Token**, click **Reset Token**, confirm, and **Copy** your new Bot Token. Save it temporarily.
5. Scroll down to **Privileged Gateway Intents** and enable:
   - ✅ **Message Content Intent** *(Required so the bot can read commands)*.
6. Click **Save Changes**.

---

### Step 2: Invite the Bot to Your Discord Server
1. In the Developer Portal left sidebar, click **Installation** (or **OAuth2 > URL Generator**).
2. Under **Scopes**, select:
   - ✅ `bot`
3. Under **Bot Permissions**, check:
   - ✅ `Send Messages`
   - ✅ `Read Message History`
   - ✅ `Embed Links`
4. Copy the generated **Install Link**, open it in your browser, choose your Discord server, and click **Authorize**.

---

### Step 3: Get Your Channel ID & Discord User ID
1. In Discord (Desktop or Web), go to **User Settings > Advanced** and turn on **Developer Mode**.
2. **Channel ID**:
   - Right-click the channel where you want Katalyst to chat (e.g., `#katalyst-remote`).
   - Click **Copy Channel ID** at the bottom of the menu.
   *(Note: If the channel is private, ensure `katalyst-bot` is added to the channel under Channel Settings > Permissions).*
3. **User ID (For Security Whitelist)**:
   - Right-click your own profile picture or username in Discord.
   - Click **Copy User ID**.

---

### Step 4: Configure Katalyst Settings
Open your `~/.config/zed/settings.json` (or click **Discord remote** in the Katalyst sidebar, then click **Edit in settings.json**).

Add the `katalyst.discord` configuration block:

```json
{
  "katalyst.discord": {
    "enabled": true,
    "bot_token": "PASTE_YOUR_DISCORD_BOT_TOKEN_HERE",
    "channel_id": "PASTE_YOUR_CHANNEL_ID_HERE",
    "authorized_user_ids": [
      "PASTE_YOUR_USER_ID_HERE"
    ]
  }
}
```

> **Security Note**: Putting your User ID in `authorized_user_ids` ensures that **only you** can control your Mac. Any messages from unauthorized users will be automatically rejected.

---

### Step 5: Start the Remote Bridge Daemon
Run the bridge daemon in the background:

```bash
~/.katalyst/bin/katalyst-discord-bridge.ts &
```

You will see:
```text
[katalyst-discord-bridge] Starting Katalyst v0.3.0 Discord Bridge...
[katalyst-discord-bridge] Connected to Discord Gateway WebSocket.
```
Your bot will now appear **Online** in your Discord server!

---

## 🎮 Discord Remote Commands Reference

Type any of these commands in your connected Discord channel:

| Command | Action & Description | Example |
|---|---|---|
| **`/help`** or **`/commands`** | Displays the full interactive command guide embed. | `/help` |
| **`/projects`** | Lists available folders in `~/Documents/Projects/` with numbers. | `/projects` |
| **`/open <number/name>`** | Opens that project window directly in Katalyst on your Mac. | `/open 1` or `/open my-app` |
| **`/threads`** | Lists recent active threads from your Katalyst sidebar. | `/threads` |
| **`/thread <number/name>`** | Switches which thread your remote prompts target. | `/thread 1` or `/thread auth-task` |
| **`/status`** | Checks bridge connection, selected thread, and Mac disk space. | `/status` |
| **`/approve`** | Approves the pending plan and starts execution (`/go`). | `/approve` |
| **`/continue`** | Sends a continue signal when the agent pauses for confirmation. | `/continue` |
| **`/abort`** | Cancels / aborts the currently running task on your Mac. | `/abort` |
| **💬 Regular Chat** | Any text without `/` is forwarded directly as a coding instruction. | *"Create a test suite for login endpoint"* |

---

## ❓ Frequently Asked Questions (FAQ)

### 1. Error: `HTTP Error 403: Forbidden (Missing Access 50001)`
* **Cause**: The bot has not been added to your Discord server, or the target channel is **Private (locked)** and the bot has not been given permission to view it.
* **Fix**:
  1. Open the invite link in Step 2 to add the bot to your server.
  2. If using a private channel, right-click the channel > **Edit Channel > Permissions > Add members or roles** > add `katalyst-bot` and enable **View Channel** & **Send Messages**.

### 2. Can strangers or server members run commands on my Mac?
* **No.** The bridge enforces strict author verification. If a message comes from an author whose User ID is not listed in `authorized_user_ids`, the bridge drops the command and sends an access denied notification.

### 3. How do I stop or restart the bridge?
* To restart: `pkill -f katalyst-discord-bridge.ts && ~/.katalyst/bin/katalyst-discord-bridge.ts &`
* To check logs: `ps aux | grep katalyst-discord-bridge`
