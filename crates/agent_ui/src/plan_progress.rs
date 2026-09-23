//! Client-side plan checklist seeding + progress for ACP agents (e.g. OMP)
//! that do not emit `SessionUpdate::Plan` during `/go` execution.
//!
//! Reuses existing `AcpThread::update_plan` / activity-bar UI — does not invent
//! a second checklist widget.

use std::path::Path;

use agent_client_protocol::schema::v1 as acp;

const MAX_PLAN_ENTRIES: usize = 20;

/// Parse execution steps from a Katalyst/OMP plan markdown file.
///
/// Preference order:
/// 1. `### Phase N:` / `### Phase N —` headings (anywhere, typically under Approach)
/// 2. Checkbox / bullet lines under `## Approach` until the next `## ` heading
pub fn parse_plan_phases(markdown: &str) -> Vec<String> {
    let mut phases = Vec::new();
    for line in markdown.lines() {
        let trimmed = line.trim();
        if let Some(rest) = trimmed.strip_prefix("### Phase ") {
            let name = rest
                .trim_start_matches(|c: char| c.is_ascii_digit())
                .trim_start_matches([':', '—', '-', ' '])
                .trim();
            if !name.is_empty() {
                phases.push(name.to_string());
            } else {
                phases.push(format!("Phase {}", phases.len() + 1));
            }
        }
        if phases.len() >= MAX_PLAN_ENTRIES {
            return phases;
        }
    }
    if !phases.is_empty() {
        return phases;
    }

    let mut in_approach = false;
    for line in markdown.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("## ") {
            in_approach = trimmed.eq_ignore_ascii_case("## Approach")
                || trimmed.to_ascii_lowercase().starts_with("## approach");
            continue;
        }
        if !in_approach {
            continue;
        }
        let item = trimmed
            .strip_prefix("- [ ] ")
            .or_else(|| trimmed.strip_prefix("- [x] "))
            .or_else(|| trimmed.strip_prefix("- [X] "))
            .or_else(|| trimmed.strip_prefix("- "))
            .or_else(|| {
                if trimmed
                    .chars()
                    .next()
                    .is_some_and(|c| c.is_ascii_digit())
                {
                    trimmed
                        .trim_start_matches(|c: char| c.is_ascii_digit())
                        .strip_prefix(". ")
                        .or_else(|| {
                            trimmed
                                .trim_start_matches(|c: char| c.is_ascii_digit())
                                .strip_prefix(") ")
                        })
                } else {
                    None
                }
            });
        if let Some(text) = item {
            let text = text.trim();
            if !text.is_empty() && !text.starts_with('`') {
                phases.push(text.to_string());
            }
        }
        if phases.len() >= MAX_PLAN_ENTRIES {
            break;
        }
    }
    phases
}

pub fn read_plan_phases(path: &Path) -> Vec<String> {
    std::fs::read_to_string(path)
        .ok()
        .map(|s| parse_plan_phases(&s))
        .unwrap_or_default()
}

/// Extract plan path from a `/go <path>` slash command (optional quotes).
pub fn plan_path_from_go_command(text: &str) -> Option<std::path::PathBuf> {
    let trimmed = text.trim();
    let rest = trimmed
        .strip_prefix("/go ")
        .or_else(|| trimmed.strip_prefix("/go\t"))?;
    let rest = rest.trim();
    if rest.is_empty() {
        return None;
    }
    let path = if (rest.starts_with('"') && rest.ends_with('"'))
        || (rest.starts_with('\'') && rest.ends_with('\''))
    {
        &rest[1..rest.len() - 1]
    } else {
        rest.split_whitespace().next().unwrap_or(rest)
    };
    if path.is_empty() {
        None
    } else {
        Some(std::path::PathBuf::from(path))
    }
}

/// Build an ACP plan: entries before `in_progress_index` Completed,
/// that index InProgress (if in range), rest Pending.
pub fn build_acp_plan(phases: &[String], in_progress_index: usize) -> acp::Plan {
    let entries = phases
        .iter()
        .enumerate()
        .map(|(i, content)| {
            let status = if i < in_progress_index {
                acp::PlanEntryStatus::Completed
            } else if i == in_progress_index {
                acp::PlanEntryStatus::InProgress
            } else {
                acp::PlanEntryStatus::Pending
            };
            acp::PlanEntry::new(content.clone(), acp::PlanEntryPriority::Medium, status)
        })
        .collect();
    acp::Plan::new(entries)
}

pub fn all_completed_plan(phases: &[String]) -> acp::Plan {
    let entries = phases
        .iter()
        .map(|content| {
            acp::PlanEntry::new(
                content.clone(),
                acp::PlanEntryPriority::Medium,
                acp::PlanEntryStatus::Completed,
            )
        })
        .collect();
    acp::Plan::new(entries)
}

/// Highest `Phase N done` found in assistant text (1-based). Also detects Plan complete.
pub fn progress_from_assistant_text(text: &str, phase_count: usize) -> ProgressHint {
    if phase_count == 0 {
        return ProgressHint::None;
    }
    let mut saw_complete = false;
    let mut max_done = 0usize;
    for line in text.lines() {
        let line = line.trim();
        let lower = line.to_ascii_lowercase();
        if lower.starts_with("plan complete") {
            saw_complete = true;
            continue;
        }
        if let Some(rest) = line.strip_prefix("Phase ").or_else(|| {
            // case-insensitive "phase "
            if lower.starts_with("phase ") {
                Some(&line["phase ".len()..])
            } else {
                None
            }
        }) {
            let digits: String = rest.chars().take_while(|c| c.is_ascii_digit()).collect();
            if digits.is_empty() {
                continue;
            }
            let after = rest[digits.len()..].trim_start();
            let after_lower = after.to_ascii_lowercase();
            if after_lower.starts_with("done") {
                if let Ok(n) = digits.parse::<usize>() {
                    max_done = max_done.max(n);
                }
            }
        }
    }
    if saw_complete {
        return ProgressHint::AllComplete;
    }
    if max_done == 0 {
        ProgressHint::None
    } else if max_done >= phase_count {
        ProgressHint::AllComplete
    } else {
        // Phase N done → next in progress is index N (0-based)
        ProgressHint::InProgressIndex(max_done)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ProgressHint {
    None,
    /// 0-based index that should be InProgress (entries before it Completed).
    InProgressIndex(usize),
    AllComplete,
}

/// Contiguous completed count from on-disk `- [x]` lines matching phase titles.
pub fn completed_count_from_disk(path: &Path, phases: &[String]) -> usize {
    let Ok(markdown) = std::fs::read_to_string(path) else {
        return 0;
    };
    let lower = markdown.to_ascii_lowercase();
    let mut completed = 0;
    for phase in phases {
        let needle = format!("- [x] {}", phase.to_ascii_lowercase());
        let needle2 = format!("- [X] {}", phase);
        if lower.contains(&needle) || markdown.contains(&needle2) {
            completed += 1;
        } else {
            break;
        }
    }
    completed
}


#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PlanProposalInfo {
    pub title: String,
    pub summary: String,
    pub plan_path: std::path::PathBuf,
}

/// Calculate current 1-based phase index and total phases for header ratio chip (e.g. 2/6).
pub fn plan_phase_ratio(completed: u32, total: usize, in_progress: bool) -> (usize, usize) {
    let current = if in_progress {
        (completed as usize + 1).min(total)
    } else {
        (completed as usize).min(total)
    };
    (current, total)
}

/// Extract "Active skills: <list>" from the first few lines of an assistant message.
/// Returns (skills_summary, remaining_markdown_body).
pub fn extract_active_skills(text: &str) -> Option<(String, String)> {
    let mut lines = Vec::new();
    let mut skills = None;
    let mut split_ix = 0;

    for (i, line) in text.lines().enumerate() {
        if i < 5 && skills.is_none() {
            let trimmed = line.trim();
            if let Some(rest) = trimmed
                .strip_prefix("Active skills:")
                .or_else(|| trimmed.strip_prefix("active skills:"))
            {
                let s = rest.trim();
                if !s.is_empty() && !s.eq_ignore_ascii_case("none | subagent: none") {
                    skills = Some(s.to_string());
                    split_ix = lines.len();
                    continue;
                }
            }
        }
        lines.push(line);
    }

    skills.map(|skills_text| {
        let remaining = if split_ix < lines.len() {
            lines[split_ix..].join("\n")
        } else {
            String::new()
        };
        (skills_text, remaining.trim_start_matches(['\r', '\n']).to_string())
    })
}

/// Returns whether an elicitation is the plan-review gate.
pub fn is_plan_review_request(text: &str) -> bool {
    text.contains("Approve plan \"")
        || (text.to_ascii_lowercase().contains("approve plan")
            && (text.contains(".plan.md") || text.contains("-plan.md")))
}

/// Detect whether text contains a proposal/mention of a plan file, and extract title/summary.
pub fn extract_plan_proposal_info(text: &str) -> Option<PlanProposalInfo> {
    let Some(home) = std::env::var_os("HOME") else {
        return None;
    };
    let home_path = std::path::Path::new(&home);

    // Look for path candidates ending in .plan.md or -plan.md, or local://...
    let mut found_path = None;
    for word in text.split_whitespace() {
        let clean = word.trim_matches(|c: char| c == '`' || c == '\'' || c == '"' || c == '(' || c == ')' || c == '<' || c == '>');
        if clean.ends_with(".plan.md") || clean.ends_with("-plan.md") {
            if clean.starts_with("~/") {
                found_path = Some(home_path.join(&clean[2..]));
                break;
            } else if clean.starts_with('/') {
                found_path = Some(std::path::PathBuf::from(clean));
                break;
            } else if let Some(slug) = clean.strip_prefix("local://") {
                let disk_slug = if slug.ends_with("-plan.md") {
                    format!("{}.plan.md", &slug[..slug.len() - "-plan.md".len()])
                } else {
                    slug.to_string()
                };
                found_path = Some(home_path.join(".cursor/plans").join(disk_slug));
                break;
            }
        }
    }

    let plan_path = found_path?;
    if !plan_path.is_file() {
        return None;
    }

    let content = std::fs::read_to_string(&plan_path).ok()?;
    let mut title = "Implementation Plan".to_string();
    let mut in_context = false;
    let mut context_lines = Vec::new();

    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("# Plan:") {
            title = trimmed["# Plan:".len()..].trim().to_string();
        } else if trimmed.starts_with("# ") && title == "Implementation Plan" {
            title = trimmed[2..].trim().to_string();
        }

        if trimmed.starts_with("## Context") {
            in_context = true;
            continue;
        } else if trimmed.starts_with("## ") && in_context {
            in_context = false;
        }

        if in_context && !trimmed.is_empty() && context_lines.len() < 2 {
            context_lines.push(trimmed);
        }
    }

    let summary = if !context_lines.is_empty() {
        context_lines.join(" ")
    } else {
        format!("Plan with {} execution steps.", parse_plan_phases(&content).len())
    };

    Some(PlanProposalInfo {
        title,
        summary,
        plan_path,
    })
}


#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_phase_headings() {
        let md = r#"
## Approach
### Phase 1 — Verify emissions
- [ ] detail
### Phase 2: Seed checklist
### Phase 3 — Context meter
"#;
        let phases = parse_plan_phases(md);
        assert_eq!(
            phases,
            vec![
                "Verify emissions".to_string(),
                "Seed checklist".to_string(),
                "Context meter".to_string(),
            ]
        );
    }

    #[test]
    fn parses_approach_checkboxes_when_no_phase_headings() {
        let md = r#"
## Approach
- [ ] First step
- [ ] Second step
## Verification
- [ ] not counted
"#;
        assert_eq!(
            parse_plan_phases(md),
            vec!["First step".to_string(), "Second step".to_string()]
        );
    }

    #[test]
    fn progress_parses_phase_done_and_complete() {
        assert_eq!(
            progress_from_assistant_text("Phase 2 done: Seed\n", 4),
            ProgressHint::InProgressIndex(2)
        );
        assert_eq!(
            progress_from_assistant_text("Plan complete. 4/4 phases done.\n", 4),
            ProgressHint::AllComplete
        );
    }

    #[test]
    fn extracts_go_path() {
        assert_eq!(
            plan_path_from_go_command("/go /tmp/foo.plan.md"),
            Some(std::path::PathBuf::from("/tmp/foo.plan.md"))
        );
        assert_eq!(
            plan_path_from_go_command("/go \"/tmp/bar plan.md\""),
            Some(std::path::PathBuf::from("/tmp/bar plan.md"))
        );
    }

    #[test]
    fn test_plan_phase_ratio_calculation() {
        assert_eq!(plan_phase_ratio(0, 6, true), (1, 6));
        assert_eq!(plan_phase_ratio(1, 6, true), (2, 6));
        assert_eq!(plan_phase_ratio(2, 6, false), (2, 6));
        assert_eq!(plan_phase_ratio(6, 6, false), (6, 6));
    }

    #[test]
    fn test_extract_active_skills() {
        let text = "Active skills: token-saving, caveman-lite\n\nHere is the plan.";
        let (skills, body) = extract_active_skills(text).expect("should extract skills");
        assert_eq!(skills, "token-saving, caveman-lite");
        assert_eq!(body, "Here is the plan.");
    }

    #[test]
    fn detects_plan_review_requests_only() {
        assert!(is_plan_review_request(
            "Approve plan \"sdk36-fix\" in ~/.katalyst/plans/sdk36-fix.plan.md"
        ));
        assert!(!is_plan_review_request(
            "Plan saved to ~/.katalyst/plans/sdk36-fix.plan.md"
        ));
    }

}
