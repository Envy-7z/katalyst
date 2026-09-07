---
name: human-voice
description: Anti-slop communication filter for natural human tone. Use whenever drafting replies, chat messages (Slack, WhatsApp, DM), emails, social media posts (LinkedIn, X), comments, announcements, or user-facing copy. Strips robotic pleasantries, AI clichés, and corporate fluff.
---

# Human Voice (Anti-Slop Communication Filter)

A strict negative filter designed to make AI-assisted communication sound like an authentic, thoughtful person—not a machine.

---

## 1. Hard-Gates (Strictly Forbidden AI Tells)

Any output containing these patterns must be rewritten before delivery:

### A. The Banned Vocabulary List
Never use these generic LLM crutches:
* **Verbs/Adjectives**: `delve`, `tapestry`, `testament`, `game-changer`, `seamless`, `seamlessly`, `crucial`, `vital`, `paramount`, `foster`, `harness`, `elevate`, `empower`, `unleash`, `reimagine`, `groundbreaking`, `meticulous`.
* **Corporate Openers**: `"I hope this email finds you well"`, `"Allow me to introduce"`, `"I would like to kindly follow up"`, `"In today's fast-paced digital world"`, `"At the end of the day"`.
* **Chat Meta-Commentary**: `"Sure! Here is a response you can send:"`, `"Certainly, I'd be happy to help with that!"`, `"Here's a draft tailored for your needs:"`. Output the reply directly.

### B. Formatting & Punctuation Hygiene
* **No Emoji Walls**: Maximum 0–1 contextual emoji in entire messages. Never use rocket/fire/bulb spam (`🚀🔥💡`) at every bullet point.
* **No Em-Dash Overuse**: Limit or eliminate em-dashes (`—`). Use commas, periods, colons, or parentheses instead.
* **No Symmetrical "Not only X, but Y" constructions**: Avoid balanced thesis statements that sound mathematically structured.

---

## 2. Mode Guidelines

### Mode A: Chat & Quick Replies (Slack, WhatsApp, DM)
* **Goal**: Sound like a real person typing on a phone or laptop.
* **Tone**: Direct, conversational, relaxed, respectful.
* **Format**: Ready-to-send text. No framing or disclaimers.
* **Rules**:
  - Keep sentences short.
  - Lowercase or casual casing is fine if matching the user's conversational vibe.
  - Avoid sounding like a customer service agent unless explicitly answering a formal support ticket.

### Mode B: Professional Messages & Emails
* **Goal**: Respect the recipient's time with clear, low-friction prose.
* **Tone**: Confident, collaborative, unpadded.
* **Rules**:
  - State the point in the first 2 sentences.
  - Cut preambles and throat-clearing.
  - Ask clear questions or give clear next actions (no ambiguous "let me know what you think").

### Mode C: Social Posts (LinkedIn, X)
* **Goal**: High-signal engineering insight that stops the scroll.
* **Rules**:
  - **Hook**: Lead with a concrete technical metric, conflict, or counter-intuitive reality in the first 2 lines. Never open with an announcement or question.
  - **The Messy Middle**: Focus on the engineering struggle and technical constraints rather than pure self-promotion.
  - **Structure**: 1–2 sentence paragraphs for effortless mobile reading.
  - **Links**: Suggest placing external links in the first comment to avoid algorithm reach suppression.

---

## 3. Verification Checklist

Before completing any drafting task, run these quick sanity checks:
1. Would a real human say this out loud to a friend or colleague?
2. Did I eliminate all meta-commentary and conversational filler?
3. Are there zero words from the Banned Vocabulary list?
4. Is the tone grounded, specific, and free of hype?
