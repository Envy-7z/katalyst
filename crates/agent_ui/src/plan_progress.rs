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
}
