use std::path::PathBuf;

use agent_ui::AgentPanel;
use editor::{Editor, MultiBufferOffset};
use gpui::{Anchor, AnyElement, ClipboardItem, Entity};
use project::ProjectPath;
use ui::{ButtonSize, ContextMenu, LabelSize, PopoverMenu, Tooltip, prelude::*};
use workspace::Toast;
use workspace::notifications::NotificationId;

use super::QuickActionBar;

struct PlanBuildToast;

impl QuickActionBar {
    pub fn render_plan_build_button(&self, cx: &mut Context<Self>) -> Option<AnyElement> {
        // Prefer source editor even when the active tab is MarkdownPreviewView.
        let editor = self.active_editor_or_preview(cx)?;
        let plan_path = plan_path_for_editor(&editor, cx)?;

        let workspace_handle = self.workspace.clone();

        // Model Selector Button (Cursor-like "[ Auto ˅ ]")
        let active_model_name = workspace_handle
            .upgrade()
            .and_then(|ws| ws.read(cx).panel::<AgentPanel>(cx))
            .and_then(|panel| panel.read(cx).active_model_name(cx));
        let model_label = active_model_name.unwrap_or_else(|| "Auto".into());

        let model_button = {
            let workspace_handle = workspace_handle.clone();
            Button::new("plan-select-model", model_label)
                .label_size(LabelSize::Small)
                .size(ButtonSize::Compact)
                .style(ButtonStyle::Subtle)
                .end_icon(
                    Icon::new(IconName::ChevronDown)
                        .size(IconSize::XSmall)
                        .color(Color::Muted),
                )
                .tooltip(Tooltip::text("Select execution model in Agent Panel"))
                .on_click(move |_, window, cx| {
                    let Some(workspace) = workspace_handle.upgrade() else {
                        return;
                    };
                    workspace.update(cx, |workspace, cx| {
                        if let Some(panel) = workspace.focus_panel::<AgentPanel>(window, cx) {
                            panel.update(cx, |panel, cx| {
                                panel.toggle_model_selector(window, cx);
                            });
                        }
                    });
                })
        };

        let build_plan_path = plan_path.clone();
        let build_workspace_handle = workspace_handle.clone();
        let build_button = Button::new("plan-build-locally", "Build Locally")
            .label_size(LabelSize::Small)
            .size(ButtonSize::Compact)
            .style(ButtonStyle::Subtle)
            .start_icon(
                Icon::new(IconName::PlayOutlined)
                    .size(IconSize::Small)
                    .color(Color::Accent),
            )
            .tooltip(Tooltip::text("Run /go on this plan in the Agent Panel"))
            .on_click(move |_, window, cx| {
                let Some(workspace) = build_workspace_handle.upgrade() else {
                    return;
                };
                let command = format!("/go {}", build_plan_path.display());
                workspace.update(cx, |workspace, cx| {
                    if let Some(panel) = workspace.focus_panel::<AgentPanel>(window, cx) {
                        let submitted = panel.update(cx, |panel, cx| {
                            panel.submit_slash_command(&command, window, cx)
                        });
                        if submitted {
                            workspace.show_toast(
                                Toast::new(
                                    NotificationId::unique::<PlanBuildToast>(),
                                    "Building plan via /go…",
                                )
                                .autohide(),
                                cx,
                            );
                            return;
                        }
                    }

                    cx.write_to_clipboard(ClipboardItem::new_string(command.clone()));
                    workspace.show_toast(
                        Toast::new(
                            NotificationId::unique::<PlanBuildToast>(),
                            "Open an OMP agent thread first — /go command copied to clipboard",
                        )
                        .autohide(),
                        cx,
                    );
                });
            });

        let overflow_menu = {
            let plan_path = plan_path.clone();
            PopoverMenu::new("plan-more-actions")
                .anchor(Anchor::TopRight)
                .menu(move |window, cx| {
                    let plan_path = plan_path.clone();
                    let menu = ContextMenu::build(window, cx, move |menu, _, _| {
                        let plan_path = plan_path.clone();
                        menu.entry("Copy as Markdown", None, {
                            let plan_path = plan_path.clone();
                            move |_window, cx| {
                                if let Ok(text) = std::fs::read_to_string(&plan_path) {
                                    cx.write_to_clipboard(ClipboardItem::new_string(text));
                                }
                            }
                        })
                        .entry("Copy Plan Path", None, {
                            let plan_path = plan_path.clone();
                            move |_window, cx| {
                                cx.write_to_clipboard(ClipboardItem::new_string(
                                    plan_path.display().to_string(),
                                ));
                            }
                        })
                    });
                    Some(menu)
                })
                .trigger_with_tooltip(
                    IconButton::new("plan-more-options", IconName::Ellipsis)
                        .icon_size(IconSize::Small)
                        .style(ButtonStyle::Subtle),
                    Tooltip::text("More Plan Actions"),
                )
        };

        let close_button = IconButton::new("plan-close-preview", IconName::Close)
            .icon_size(IconSize::Small)
            .style(ButtonStyle::Subtle)
            .tooltip(Tooltip::text("Hide Plan Panel"))
            .on_click({
                let workspace_handle = workspace_handle.clone();
                move |_, window, cx| {
                    if let Some(workspace) = workspace_handle.upgrade() {
                        workspace.update(cx, |workspace, cx| {
                            let active_pane = workspace.active_pane().clone();
                            active_pane.update(cx, |pane, cx| {
                                pane.close_active_item(&Default::default(), window, cx);
                            });
                        });
                    }
                }
            });

        Some(
            h_flex()
                .gap(DynamicSpacing::Base01.rems(cx))
                .child(model_button)
                .child(build_button)
                .child(overflow_menu)
                .child(close_button)
                .into_any_element(),
        )
    }
}

fn plan_path_for_editor(editor: &Entity<Editor>, cx: &App) -> Option<PathBuf> {
    let editor = editor.read(cx);
    let file = editor.file_at(MultiBufferOffset(0), cx)?;
    let project_path = ProjectPath::from_file(file.as_ref(), cx);
    let absolute_path = editor
        .project()
        .and_then(|project| project.read(cx).absolute_path(&project_path, cx))
        .or_else(|| file.as_local().map(|file| file.abs_path(cx)))?;

    let name = absolute_path.file_name()?.to_string_lossy();
    if is_plan_filename(&name) {
        Some(absolute_path)
    } else {
        None
    }
}

/// Katalyst convention is `*.plan.md`. OMP plan-mode local:// paths historically
/// mirrored as `*-plan.md`; accept both so the Build toolbar stays visible.
pub(crate) fn is_plan_filename(name: &str) -> bool {
    name.ends_with(".plan.md") || name.ends_with("-plan.md")
}
