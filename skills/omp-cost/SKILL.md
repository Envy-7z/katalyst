---
name: omp-cost
description: >-
  Inspect detailed token usage, prompt caching efficiency, and API costs
  broken down by calendar month, model, workspace, and agent architecture for
  Oh My Pi. Use when the user asks about API spending, token burn rate, prompt
  cache dollar savings, or invokes /omp-cost.
---

# Oh My Pi Usage & Cost Analyzer (`omp-cost`)

`omp-cost` inspects detailed token usage, prompt caching efficiency, and API costs broken down by calendar month for individual profiles or all profiles. It queries local session transcripts and SQLite databases managed by Oh My Pi.

Binary location: `/Users/wisnuu/.local/bin/omp-cost` (in `$PATH`).

## Quick Invocations

Run via `bash`:

```bash
# Summary of current month across all providers and models
omp-cost

# Clean Markdown report with tables (ideal for chat output)
omp-cost -o md

# Breakdown by workspace repository / project
omp-cost --by-project

# Breakdown by agent architecture (orchestrator vs subagents)
omp-cost --by-agent

# Prompt cache ROI and dollar savings
omp-cost --savings

# Daily burn rate and month-end forecast with budget alert
omp-cost --forecast --budget 150

# Day-by-day cost and token breakdown
omp-cost -d

# Week-by-week breakdown
omp-cost -w

# Specific profile and historical month
omp-cost default 2026-08

# Fast query (<15ms) bypassing transcript sync
omp-cost --no-sync

# Machine-readable JSON output
omp-cost -o json
```

## JSON Output Structure (`-o json`)

When programmatic parsing or charting is required, `omp-cost -o json` outputs structured metrics:

```json
{
  "month": "2026-09",
  "total_requests": 37286,
  "total_input_tokens": 52028064,
  "total_output_tokens": 770194,
  "total_cache_tokens": 551580252,
  "total_cost": 91.156,
  "total_cost_no_cache": 482.124,
  "total_savings": {
    "net_spend": 91.156,
    "estimated_no_cache": 482.124,
    "dollars_saved": 390.967,
    "savings_pct": 81.09
  },
  "combined_forecast": {
    "month": "2026-09",
    "active_days": 15,
    "total_days_in_month": 30,
    "current_spend": 91.156,
    "daily_burn_rate": 6.077,
    "projected_spend": 182.312,
    "over_budget": false
  },
  "profiles": [
    {
      "profile": "default",
      "providers": [
        {
          "provider": "google-antigravity",
          "models": [
            {
              "model": "gemini-3.8-flash",
              "requests": 1952,
              "cost": 81.707,
              "share_pct": 89.63
            }
          ]
        }
      ],
      "projects": [
        {
          "display_name": "history",
          "cost": 78.39,
          "share_pct": 85.99
        }
      ],
      "agent_types": [
        { "agent_type": "main", "cost": 84.78, "share_pct": 93.01 },
        { "agent_type": "subagent", "cost": 6.36, "share_pct": 6.98 }
      ]
    }
  ]
}
```

## Cost Optimization Guidelines

When analyzing usage or advising the user on token efficiency:
1. **Prompt Cache Leverage**: Check `cache_hit` percentage and `savings_pct`. High prompt cache hits (>90%) provide an ~80% discount over uncached pricing.
2. **Model Tiering**: Route broad codebase searches, formatting, and scout tasks to fast/economical models like `google-antigravity/gemini-3.8-flash`. Reserve reasoning-heavy or expensive models (`claude-opus-4-6`, `gemini-3.1-pro`) for high-complexity decisions.
3. **Budget Guardrails**: Use `omp-cost --forecast --budget <N>` to alert when projected month-end spend exceeds planned thresholds.
