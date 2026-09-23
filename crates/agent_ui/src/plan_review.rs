use std::any::TypeId;
use std::path::{Component, PathBuf};

use agent_client_protocol::schema::v1 as acp;
use anyhow::{Context as _, Result};

#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub(crate) struct PlanReviewKey {
    pub(crate) session_id: acp::SessionId,
    pub(crate) plan_path: PathBuf,
}

impl PlanReviewKey {
    pub(crate) fn new(session_id: acp::SessionId, plan_path: PathBuf) -> Self {
        Self {
            session_id,
            plan_path: normalize_path(plan_path),
        }
    }
}

fn normalize_path(path: PathBuf) -> PathBuf {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            Component::CurDir => {}
            Component::ParentDir if !normalized.pop() => normalized.push(component.as_os_str()),
            _ => normalized.push(component.as_os_str()),
        }
    }
    normalized
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PlanReviewMode {
    Rendered,
    Source,
}

impl PlanReviewMode {
    fn toggle(&mut self) {
        *self = match self {
            Self::Rendered => Self::Source,
            Self::Source => Self::Rendered,
        };
    }

    fn to_db(self) -> i64 {
        match self {
            Self::Rendered => 0,
            Self::Source => 1,
        }
    }

    fn from_db(value: i64) -> Self {
        match value {
            1 => Self::Source,
            _ => Self::Rendered,
        }
    }
}
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PlanReviewAvailability {
    Ready,
    MissingFile,
    SessionUnavailable,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub(crate) enum PlanReviewStepStatus {
    Pending,
    InProgress,
    Completed,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PlanReviewStep {
    pub(crate) title: String,
    pub(crate) status: PlanReviewStepStatus,
}

impl PlanReviewStep {
    #[cfg(test)]
    fn pending(title: &str) -> Self {
        Self {
            title: title.to_string(),
            status: PlanReviewStepStatus::Pending,
        }
    }

    #[cfg(test)]
    fn in_progress(title: &str) -> Self {
        Self {
            title: title.to_string(),
            status: PlanReviewStepStatus::InProgress,
        }
    }

    #[cfg(test)]
    fn completed(title: &str) -> Self {
        Self {
            title: title.to_string(),
            status: PlanReviewStepStatus::Completed,
        }
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub(crate) struct PlanReviewProjection {
    pub(crate) availability: PlanReviewAvailability,
    pub(crate) steps: Vec<PlanReviewStep>,
}

pub(crate) fn project_plan(
    markdown: &str,
    live_steps: Option<&[(String, acp::PlanEntryStatus)]>,
) -> PlanReviewProjection {
    let steps = live_steps
        .filter(|steps| !steps.is_empty())
        .map(|steps| {
            steps
                .iter()
                .map(|(title, status)| PlanReviewStep {
                    title: title.clone(),
                    status: match status {
                        acp::PlanEntryStatus::Completed => PlanReviewStepStatus::Completed,
                        acp::PlanEntryStatus::InProgress => PlanReviewStepStatus::InProgress,
                        acp::PlanEntryStatus::Pending => PlanReviewStepStatus::Pending,
                        _ => PlanReviewStepStatus::Pending,
                    },
                })
                .collect()
        })
        .unwrap_or_else(|| {
            crate::plan_progress::parse_plan_phases(markdown)
                .into_iter()
                .map(|title| PlanReviewStep {
                    title,
                    status: PlanReviewStepStatus::Pending,
                })
                .collect()
        });

    PlanReviewProjection {
        availability: PlanReviewAvailability::Ready,
        steps,
    }
}

pub(crate) fn availability_for(
    plan_path: &std::path::Path,
    session_available: bool,
) -> PlanReviewAvailability {
    if !plan_path.is_file() {
        PlanReviewAvailability::MissingFile
    } else if !session_available {
        PlanReviewAvailability::SessionUnavailable
    } else {
        PlanReviewAvailability::Ready
    }
}

use gpui::{
    AnyEntity, App, AppContext as _, Context, Entity, EventEmitter, FocusHandle, Focusable,
    IntoElement, Render, SharedString, Task, WeakEntity, Window,
};
use markdown_preview::markdown_preview_view::MarkdownPreviewView;
use project::{Project, ProjectPath};
use theme::ActiveTheme;
use ui::{Icon, IconName, IconSize, Label, LabelSize, prelude::*};
use workspace::{
    delete_unloaded_items, ItemId, Workspace, WorkspaceId,
    item::{Item, ItemHandle, SaveOptions, SerializableItem},
};


pub(crate) struct PlanReviewView {
    key: PlanReviewKey,
    title: SharedString,
    source_editor: Entity<editor::Editor>,
    markdown_view: Entity<MarkdownPreviewView>,
    mode: PlanReviewMode,
    focus_handle: FocusHandle,
    projection: PlanReviewProjection,
    workspace: WeakEntity<Workspace>,
}

impl PlanReviewView {
    pub(crate) fn new(
        key: PlanReviewKey,
        title: SharedString,
        source_editor: Entity<editor::Editor>,
        markdown_view: Entity<MarkdownPreviewView>,
        projection: PlanReviewProjection,
        workspace: WeakEntity<Workspace>,
        cx: &mut Context<Self>,
    ) -> Self {
        Self {
            key,
            title,
            source_editor,
            markdown_view,
            mode: PlanReviewMode::Rendered,
            focus_handle: cx.focus_handle(),
            projection,
            workspace,
        }
    }
    pub(crate) fn key(&self) -> &PlanReviewKey {
        &self.key
    }


    fn render_header(&self, cx: &Context<Self>) -> impl IntoElement {
        let completed = self
            .projection
            .steps
            .iter()
            .filter(|step| step.status == PlanReviewStepStatus::Completed)
            .count();
        let total = self.projection.steps.len();

        h_flex()
            .w_full()
            .justify_between()
            .items_center()
            .px_3()
            .py_2()
            .border_b_1()
            .border_color(cx.theme().colors().border)
            .child(
                h_flex()
                    .min_w_0()
                    .gap_2()
                    .child(Icon::new(IconName::ListTodo).size(IconSize::Small))
                    .child(Label::new(self.title.clone()).size(LabelSize::Default)),
            )
            .child(
                Label::new(format!("{completed}/{total} steps"))
                    .size(LabelSize::Small)
                    .color(ui::Color::Muted),
            )
    }

    fn render_steps(&self, _cx: &Context<Self>) -> impl IntoElement {
        v_flex()
            .w_full()
            .px_3()
            .py_2()
            .gap_1()
            .children(self.projection.steps.iter().map(|step| {
                let icon = match step.status {
                    PlanReviewStepStatus::Completed => IconName::TodoComplete,
                    PlanReviewStepStatus::InProgress => IconName::TodoProgress,
                    PlanReviewStepStatus::Pending => IconName::TodoPending,
                };
                h_flex()
                    .gap_2()
                    .items_center()
                    .child(Icon::new(icon).size(IconSize::Small))
                    .child(
                        Label::new(step.title.clone())
                            .size(LabelSize::Small)
                            .color(ui::Color::Muted),
                    )
            }))
            .when(self.projection.steps.is_empty(), |this| {
                this.child(
                    Label::new("No execution steps available")
                        .size(LabelSize::Small)
                        .color(ui::Color::Muted),
                )
            })
    }
}

impl EventEmitter<()> for PlanReviewView {}

impl Focusable for PlanReviewView {
    fn focus_handle(&self, _: &App) -> FocusHandle {
        self.focus_handle.clone()
    }
}

impl Render for PlanReviewView {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let mode = self.mode;
        let body = match mode {
            PlanReviewMode::Rendered => self.markdown_view.clone().into_any_element(),
            PlanReviewMode::Source => self.source_editor.clone().into_any_element(),
        };
        let toggle_label = match mode {
            PlanReviewMode::Rendered => "Edit Source",
            PlanReviewMode::Source => "Render Plan",
        };

        v_flex()
            .size_full()
            .bg(cx.theme().colors().editor_background)
            .child(self.render_header(cx))
            .child(self.render_steps(cx))
            .child(div().flex_1().min_h_0().child(body))
            .child(
                h_flex()
                    .w_full()
                    .justify_end()
                    .gap_2()
                    .px_3()
                    .py_2()
                    .border_t_1()
                    .border_color(cx.theme().colors().border)
                    .child(
                        Button::new("plan-review-open-source-thread", "Open Source Thread")
                            .label_size(LabelSize::Small)
                            .size(ButtonSize::Compact)
                            .style(ButtonStyle::Subtle)
                            .on_click({
                                let workspace = self.workspace.clone();
                                let session_id = self.key.session_id.clone();
                                move |_, window, cx| {
                                    if let Some(workspace) = workspace.upgrade() {
                                        workspace.update(cx, |workspace, cx| {
                                            if let Some(panel) =
                                                workspace.panel::<crate::AgentPanel>(cx)
                                            {
                                                panel.update(cx, |panel, cx| {
                                                    panel.open_plan_source_session(
                                                        &session_id,
                                                        window,
                                                        cx,
                                                    );
                                                });
                                            }
                                        });
                                    }
                                }
                            }),
                    )
                    .child(
                        Button::new("plan-review-build", "Approve & Build")
                            .label_size(LabelSize::Small)
                            .size(ButtonSize::Compact)
                            .style(ButtonStyle::Filled)
                            .on_click({
                                let workspace = self.workspace.clone();
                                let session_id = self.key.session_id.clone();
                                let plan_path = self.key.plan_path.clone();
                                move |_, window, cx| {
                                    if let Some(workspace) = workspace.upgrade() {
                                        workspace.update(cx, |workspace, cx| {
                                            if let Some(panel) =
                                                workspace.panel::<crate::AgentPanel>(cx)
                                            {
                                                panel.update(cx, |panel, cx| {
                                                    let _ = panel.submit_plan_for_session(
                                                        &session_id,
                                                        &plan_path,
                                                        window,
                                                        cx,
                                                    );
                                                });
                                            }
                                        });
                                    }
                                }
                            }),
                    )
                    .child(
                        Button::new("plan-review-toggle-source", toggle_label)
                            .label_size(LabelSize::Small)
                            .size(ButtonSize::Compact)
                            .style(ButtonStyle::Subtle)
                            .on_click(cx.listener(|this, _, _, cx| {
                                this.mode.toggle();
                                cx.emit(());
                                cx.notify();
                            })),
                    ),
            )
    }
}

impl Item for PlanReviewView {
    type Event = ();

    fn tab_content_text(&self, _: usize, _: &App) -> SharedString {
        self.title.clone()
    }

    fn tab_icon(&self, _: &Window, _: &App) -> Option<Icon> {
        Some(Icon::new(IconName::ListTodo))
    }

    fn telemetry_event_text(&self) -> Option<&'static str> {
        Some("Plan Review Opened")
    }

    fn buffer_kind(&self, cx: &App) -> workspace::item::ItemBufferKind {
        self.source_editor.read(cx).buffer_kind(cx)
    }

    fn active_project_path(&self, cx: &App) -> Option<ProjectPath> {
        self.source_editor.read(cx).active_project_path(cx)
    }

    fn is_dirty(&self, cx: &App) -> bool {
        self.source_editor.read(cx).is_dirty(cx)
    }

    fn has_deleted_file(&self, cx: &App) -> bool {
        self.source_editor.read(cx).has_deleted_file(cx)
    }

    fn has_conflict(&self, cx: &App) -> bool {
        self.source_editor.read(cx).has_conflict(cx)
    }

    fn can_save(&self, cx: &App) -> bool {
        self.source_editor.read(cx).can_save(cx)
    }

    fn save(
        &mut self,
        options: SaveOptions,
        project: Entity<Project>,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) -> Task<Result<()>> {
        self.source_editor.save(options, project, window, cx)
    }

    fn save_as(
        &mut self,
        project: Entity<Project>,
        path: ProjectPath,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) -> Task<Result<()>> {
        self.source_editor.save_as(project, path, window, cx)
    }

    fn reload(
        &mut self,
        project: Entity<Project>,
        window: &mut Window,
        cx: &mut Context<Self>,
    ) -> Task<Result<()>> {
        self.source_editor.reload(project, window, cx)
    }

    fn act_as_type<'a>(
        &'a self,
        type_id: TypeId,
        self_handle: &'a Entity<Self>,
        cx: &'a App,
    ) -> Option<AnyEntity> {
        if type_id == TypeId::of::<editor::Editor>() {
            Some(self.source_editor.clone().into())
        } else {
            <Self as Item>::act_as_type(self, type_id, self_handle, cx)
        }
    }
}

impl SerializableItem for PlanReviewView {
    fn serialized_item_kind() -> &'static str {
        "PlanReviewView"
    }

    fn cleanup(
        workspace_id: WorkspaceId,
        alive_items: Vec<ItemId>,
        _window: &mut Window,
        cx: &mut App,
    ) -> Task<Result<()>> {
        let db = persistence::PlanReviewDb::global(cx);
        delete_unloaded_items(alive_items, workspace_id, "plan_reviews", &db, cx)
    }

    fn deserialize(
        project: Entity<Project>,
        workspace: WeakEntity<Workspace>,
        workspace_id: WorkspaceId,
        item_id: ItemId,
        window: &mut Window,
        cx: &mut App,
    ) -> Task<Result<Entity<Self>>> {
        let db = persistence::PlanReviewDb::global(cx);
        window.spawn(cx, async move |cx| {
            let (session_id, abs_path, title, mode_value) = db
                .get_review(item_id, workspace_id)?
                .context("No plan review entry found")?;
            let mode = PlanReviewMode::from_db(mode_value);
            let (worktree, relative_path) = project
                .update(cx, |project, cx| {
                    project.find_or_create_worktree(abs_path.clone(), false, cx)
                })
                .await
                .context("Path not found")?;
            let worktree_id = worktree.read_with(cx, |worktree, _| worktree.id());
            let project_path = ProjectPath {
                worktree_id,
                path: relative_path,
            };
            let buffer = project
                .update(cx, |project, cx| project.open_buffer(project_path, cx))
                .await?;
            let markdown = buffer.read_with(cx, |buffer, _| buffer.text());

            cx.update(|window, cx| {
                let language_registry = project.read(cx).languages().clone();
                let editor =
                    cx.new(|cx| editor::Editor::for_buffer(buffer, Some(project.clone()), window, cx));
                let markdown_view = MarkdownPreviewView::new(
                    markdown_preview::markdown_preview_view::MarkdownPreviewMode::Default,
                    editor.clone(),
                    workspace.clone(),
                    language_registry,
                    window,
                    cx,
                );
                let key = PlanReviewKey::new(acp::SessionId::new(session_id), abs_path.clone());
                let mut projection = project_plan(&markdown, None);
                projection.availability = availability_for(&abs_path, true);
                cx.new(|cx| {
                    let mut view = PlanReviewView::new(
                        key,
                        title.into(),
                        editor,
                        markdown_view,
                        projection,
                        workspace,
                        cx,
                    );
                    view.mode = mode;
                    view
                })
            })
        })
    }

    fn serialize(
        &mut self,
        workspace: &mut Workspace,
        item_id: ItemId,
        _closing: bool,
        cx: &mut Context<Self>,
    ) -> Option<Task<Result<()>>> {
        let workspace_id = workspace.database_id()?;
        let abs_path = self.key.plan_path.clone();
        let session_id = self.key.session_id.0.to_string();
        let title = self.title.to_string();
        let mode = self.mode.to_db();
        let db = persistence::PlanReviewDb::global(cx);
        Some(cx.background_spawn(async move {
            db.save_review(item_id, workspace_id, session_id, abs_path, title, mode)
                .await
        }))
    }

    fn should_serialize(&self, _: &Self::Event) -> bool {
        true
    }
}

mod persistence {
    use std::path::PathBuf;

    use db::{
        query,
        sqlez::{domain::Domain, thread_safe_connection::ThreadSafeConnection},
        sqlez_macros::sql,
    };
    use workspace::{ItemId, WorkspaceDb, WorkspaceId};

    pub struct PlanReviewDb(ThreadSafeConnection);

    impl Domain for PlanReviewDb {
        const NAME: &str = stringify!(PlanReviewDb);
        const MIGRATIONS: &[&str] = &[sql!(
            CREATE TABLE plan_reviews (
                workspace_id INTEGER,
                item_id INTEGER,
                session_id TEXT NOT NULL,
                abs_path BLOB NOT NULL,
                title TEXT NOT NULL,
                mode INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(workspace_id, item_id),
                FOREIGN KEY(workspace_id) REFERENCES workspaces(workspace_id)
                    ON DELETE CASCADE
            ) STRICT;
        )];
    }

    db::static_connection!(PlanReviewDb, [WorkspaceDb]);

    impl PlanReviewDb {
        query! {
            pub async fn save_review(
                item_id: ItemId,
                workspace_id: WorkspaceId,
                session_id: String,
                abs_path: PathBuf,
                title: String,
                mode: i64
            ) -> Result<()> {
                INSERT OR REPLACE INTO plan_reviews(
                    item_id, workspace_id, session_id, abs_path, title, mode
                )
                VALUES (?, ?, ?, ?, ?, ?)
            }
        }

        query! {
            pub fn get_review(
                item_id: ItemId,
                workspace_id: WorkspaceId
            ) -> Result<Option<(String, PathBuf, String, i64)>> {
                SELECT session_id, abs_path, title, mode
                FROM plan_reviews
                WHERE item_id = ? AND workspace_id = ?
            }
        }
    }
}


#[cfg(test)]
mod tests {
    use std::path::PathBuf;

    use agent_client_protocol::schema::v1 as acp;

    use super::PlanReviewKey;

    #[test]
    fn same_session_and_lexical_path_share_identity() {
        let first = PlanReviewKey::new(
            acp::SessionId::new("session-a"),
            PathBuf::from("/workspace/./plans/feature.plan.md"),
        );
        let second = PlanReviewKey::new(
            acp::SessionId::new("session-a"),
            PathBuf::from("/workspace/plans/feature.plan.md"),
        );

        assert_eq!(first, second);
    }

    #[test]
    fn same_path_from_different_sessions_is_not_reused() {
        let first = PlanReviewKey::new(
            acp::SessionId::new("session-a"),
            PathBuf::from("/workspace/plans/feature.plan.md"),
        );
        let second = PlanReviewKey::new(
            acp::SessionId::new("session-b"),
            PathBuf::from("/workspace/plans/feature.plan.md"),
        );

        assert_ne!(first, second);
    }
    #[test]
    fn projection_falls_back_to_markdown_phases_without_live_plan() {
        let projection = super::project_plan(
            "## Approach\n### Phase 1 — Inspect\n### Phase 2 — Verify\n",
            None,
        );

        assert_eq!(
            projection.steps,
            vec![
                super::PlanReviewStep::pending("Inspect"),
                super::PlanReviewStep::pending("Verify"),
            ]
        );
    }

    #[test]
    fn projection_prefers_live_acp_statuses_when_available() {
        let live_steps = vec![
            ("Inspect".to_string(), acp::PlanEntryStatus::Completed),
            ("Verify".to_string(), acp::PlanEntryStatus::InProgress),
        ];
        let projection = super::project_plan("## Approach\n- stale markdown\n", Some(&live_steps));

        assert_eq!(
            projection.steps,
            vec![
                super::PlanReviewStep::completed("Inspect"),
                super::PlanReviewStep::in_progress("Verify"),
            ]
        );
    }

    #[test]
    fn availability_reports_missing_file_before_session_state() {
        assert_eq!(
            super::availability_for(
                std::path::Path::new("/definitely/missing/feature.plan.md"),
                false,
            ),
            super::PlanReviewAvailability::MissingFile,
        );
    }

    #[test]
    fn availability_reports_unavailable_session_for_existing_file() {
        let path = std::env::temp_dir().join(format!(
            "katalyst-plan-review-{}.plan.md",
            std::process::id()
        ));
        std::fs::write(&path, "# Plan\n").unwrap();

        assert_eq!(
            super::availability_for(&path, false),
            super::PlanReviewAvailability::SessionUnavailable,
        );

        std::fs::remove_file(path).unwrap();
    }
    #[test]
    fn rendered_mode_toggles_to_source_and_back() {
        let mut mode = super::PlanReviewMode::Rendered;
        mode.toggle();
        assert_eq!(mode, super::PlanReviewMode::Source);
        mode.toggle();
        assert_eq!(mode, super::PlanReviewMode::Rendered);
    }
}
