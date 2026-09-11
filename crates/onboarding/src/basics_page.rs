use std::path::PathBuf;
use std::sync::Arc;
use std::time::Duration;

use client::{Client, UserStore, zed_urls};
use cloud_api_types::Plan;
use collections::HashMap;
use fs::Fs;
use gpui::{
    Action, Animation, AnimationExt, App, Context, Entity, IntoElement, TaskExt, pulsating_between,
};
use project::agent_server_store::AllAgentServersSettings;
use project::project_settings::ProjectSettings;
use project::{AgentRegistryStore, RegistryAgent};
use settings::{
    BaseKeymap, CustomAgentServerSettings, Settings, SettingsStore, update_settings_file,
};
use theme::{Appearance, SystemAppearance, ThemeRegistry};
use theme_settings::{ThemeAppearanceMode, ThemeName, ThemeSelection, ThemeSettings};
use ui::{
    AgentSetupButton, Divider, StatefulInteractiveElement, SwitchField, TintColor,
    ToggleButtonGroup, ToggleButtonGroupSize, ToggleButtonSimple, ToggleButtonWithIcon, Tooltip,
    prelude::*,
};
use vim_mode_setting::VimModeSetting;

use crate::{
    ImportCursorSettings, ImportVsCodeSettings, Onboarding, SettingsImportState,
    theme_preview::{ThemePreviewStyle, ThemePreviewTile},
};

const LIGHT_THEMES: [&str; 3] = ["One Light", "Ayu Light", "Gruvbox Light"];
const DARK_THEMES: [&str; 3] = ["One Dark", "Ayu Dark", "Gruvbox Dark"];
const FAMILY_NAMES: [SharedString; 3] = [
    SharedString::new_static("One"),
    SharedString::new_static("Ayu"),
    SharedString::new_static("Gruvbox"),
];

fn get_theme_family_themes(theme_name: &str) -> Option<(&'static str, &'static str)> {
    for i in 0..LIGHT_THEMES.len() {
        if LIGHT_THEMES[i] == theme_name || DARK_THEMES[i] == theme_name {
            return Some((LIGHT_THEMES[i], DARK_THEMES[i]));
        }
    }
    None
}

fn render_theme_section(tab_index: &mut isize, cx: &mut App) -> impl IntoElement {
    let theme_selection = ThemeSettings::get_global(cx).theme.clone();
    let system_appearance = theme::SystemAppearance::global(cx);

    let theme_mode = theme_selection
        .mode()
        .unwrap_or_else(|| match *system_appearance {
            Appearance::Light => ThemeAppearanceMode::Light,
            Appearance::Dark => ThemeAppearanceMode::Dark,
        });

    return v_flex()
        .gap_2()
        .child(
            h_flex().justify_between().child(Label::new("Theme")).child(
                ToggleButtonGroup::single_row(
                    "theme-selector-onboarding-dark-light",
                    [
                        ThemeAppearanceMode::Light,
                        ThemeAppearanceMode::Dark,
                        ThemeAppearanceMode::System,
                    ]
                    .map(|mode| {
                        const MODE_NAMES: [SharedString; 3] = [
                            SharedString::new_static("Light"),
                            SharedString::new_static("Dark"),
                            SharedString::new_static("System"),
                        ];
                        ToggleButtonSimple::new(
                            MODE_NAMES[mode as usize].clone(),
                            move |_, _, cx| {
                                write_mode_change(mode, cx);

                                telemetry::event!(
                                    "Welcome Theme mode Changed",
                                    from = theme_mode,
                                    to = mode
                                );
                            },
                        )
                    }),
                )
                .size(ToggleButtonGroupSize::Medium)
                .tab_index(tab_index)
                .selected_index(theme_mode as usize)
                .style(ui::ToggleButtonGroupStyle::Outlined)
                .width(rems_from_px(3.0_f32 * 64.0_f32)),
            ),
        )
        .child(
            h_flex()
                .gap_2()
                .justify_between()
                .children(render_theme_previews(tab_index, &theme_selection, cx)),
        );

    fn render_theme_previews(
        tab_index: &mut isize,
        theme_selection: &ThemeSelection,
        cx: &mut App,
    ) -> [impl IntoElement; 3] {
        let system_appearance = SystemAppearance::global(cx);
        let theme_registry = ThemeRegistry::global(cx);

        let theme_seed = 0xBEEF as f32;
        let theme_mode = theme_selection
            .mode()
            .unwrap_or_else(|| match *system_appearance {
                Appearance::Light => ThemeAppearanceMode::Light,
                Appearance::Dark => ThemeAppearanceMode::Dark,
            });
        let appearance = match theme_mode {
            ThemeAppearanceMode::Light => Appearance::Light,
            ThemeAppearanceMode::Dark => Appearance::Dark,
            ThemeAppearanceMode::System => *system_appearance,
        };
        let current_theme_name: SharedString = theme_selection.name(appearance).0.into();

        let theme_names = match appearance {
            Appearance::Light => LIGHT_THEMES,
            Appearance::Dark => DARK_THEMES,
        };

        let themes = theme_names.map(|theme| theme_registry.get(theme).unwrap());

        [0, 1, 2].map(|index| {
            let theme = &themes[index];
            let is_selected = theme.name == current_theme_name;
            let name = theme.name.clone();
            let colors = cx.theme().colors();

            v_flex()
                .w_full()
                .items_center()
                .gap_1()
                .child(
                    h_flex()
                        .id(name)
                        .relative()
                        .w_full()
                        .border_2()
                        .border_color(colors.border_transparent)
                        .rounded(ThemePreviewTile::ROOT_RADIUS)
                        .map(|this| {
                            if is_selected {
                                this.border_color(colors.border_selected)
                            } else {
                                this.opacity(0.8).hover(|s| s.border_color(colors.border))
                            }
                        })
                        .tab_index({
                            *tab_index += 1;
                            *tab_index - 1
                        })
                        .focus(|mut style| {
                            style.border_color = Some(colors.border_focused);
                            style
                        })
                        .on_click({
                            let theme_name = theme.name.clone();
                            let current_theme_name = current_theme_name.clone();

                            move |_, _, cx| {
                                write_theme_change(theme_name.clone(), theme_mode, cx);
                                telemetry::event!(
                                    "Welcome Theme Changed",
                                    from = current_theme_name,
                                    to = theme_name
                                );
                            }
                        })
                        .map(|this| {
                            if theme_mode == ThemeAppearanceMode::System {
                                let (light, dark) = (
                                    theme_registry.get(LIGHT_THEMES[index]).unwrap(),
                                    theme_registry.get(DARK_THEMES[index]).unwrap(),
                                );
                                this.child(
                                    ThemePreviewTile::new(light, theme_seed)
                                        .style(ThemePreviewStyle::SideBySide(dark)),
                                )
                            } else {
                                this.child(
                                    ThemePreviewTile::new(theme.clone(), theme_seed)
                                        .style(ThemePreviewStyle::Bordered),
                                )
                            }
                        }),
                )
                .child(
                    Label::new(FAMILY_NAMES[index].clone())
                        .color(Color::Muted)
                        .size(LabelSize::Small),
                )
        })
    }

    fn write_mode_change(mode: ThemeAppearanceMode, cx: &mut App) {
        let fs = <dyn Fs>::global(cx);
        update_settings_file(fs, cx, move |settings, _cx| {
            theme_settings::set_mode(settings, mode);
        });
    }

    fn write_theme_change(
        theme: impl Into<Arc<str>>,
        theme_mode: ThemeAppearanceMode,
        cx: &mut App,
    ) {
        let fs = <dyn Fs>::global(cx);
        let theme = theme.into();
        update_settings_file(fs, cx, move |settings, cx| match theme_mode {
            ThemeAppearanceMode::System => {
                let (light_theme, dark_theme) =
                    get_theme_family_themes(&theme).unwrap_or((theme.as_ref(), theme.as_ref()));

                settings.theme.theme = Some(settings::ThemeSelection::Dynamic {
                    mode: ThemeAppearanceMode::System,
                    light: ThemeName(light_theme.into()),
                    dark: ThemeName(dark_theme.into()),
                });
            }
            ThemeAppearanceMode::Light => theme_settings::set_theme(
                settings,
                theme,
                Appearance::Light,
                *SystemAppearance::global(cx),
            ),
            ThemeAppearanceMode::Dark => theme_settings::set_theme(
                settings,
                theme,
                Appearance::Dark,
                *SystemAppearance::global(cx),
            ),
        });
    }
}

fn render_base_keymap_section(tab_index: &mut isize, cx: &mut App) -> impl IntoElement {
    let base_keymap = match BaseKeymap::get_global(cx) {
        BaseKeymap::Zed => Some(0),
        BaseKeymap::VSCode => Some(1),
        BaseKeymap::JetBrains => Some(2),
        BaseKeymap::SublimeText => Some(3),
        BaseKeymap::Atom => Some(4),
        BaseKeymap::Emacs => Some(5),
        BaseKeymap::Cursor => Some(6),
        BaseKeymap::TextMate => Some(7),
        BaseKeymap::None => None,
    };

    return v_flex().gap_2().child(Label::new("Base Keymap")).child(
        ToggleButtonGroup::two_rows(
            "base_keymap_selection",
            [
                ToggleButtonWithIcon::new("Zed", IconName::AiZed, |_, _, cx| {
                    write_keymap_base(BaseKeymap::Zed, cx);
                }),
                ToggleButtonWithIcon::new("VS Code", IconName::EditorVsCode, |_, _, cx| {
                    write_keymap_base(BaseKeymap::VSCode, cx);
                }),
                ToggleButtonWithIcon::new("JetBrains", IconName::EditorJetBrains, |_, _, cx| {
                    write_keymap_base(BaseKeymap::JetBrains, cx);
                }),
                ToggleButtonWithIcon::new("Sublime Text", IconName::EditorSublime, |_, _, cx| {
                    write_keymap_base(BaseKeymap::SublimeText, cx);
                }),
            ],
            [
                ToggleButtonWithIcon::new("Atom", IconName::EditorAtom, |_, _, cx| {
                    write_keymap_base(BaseKeymap::Atom, cx);
                }),
                ToggleButtonWithIcon::new("Emacs", IconName::EditorEmacs, |_, _, cx| {
                    write_keymap_base(BaseKeymap::Emacs, cx);
                }),
                ToggleButtonWithIcon::new("Cursor", IconName::EditorCursor, |_, _, cx| {
                    write_keymap_base(BaseKeymap::Cursor, cx);
                }),
                ToggleButtonWithIcon::new("TextMate", IconName::Keyboard, |_, _, cx| {
                    write_keymap_base(BaseKeymap::TextMate, cx);
                }),
            ],
        )
        .when_some(base_keymap, |this, base_keymap| {
            this.selected_index(base_keymap)
        })
        .full_width()
        .tab_index(tab_index)
        .size(ui::ToggleButtonGroupSize::Medium)
        .style(ui::ToggleButtonGroupStyle::Outlined),
    );

    fn write_keymap_base(keymap_base: BaseKeymap, cx: &App) {
        let fs = <dyn Fs>::global(cx);

        update_settings_file(fs, cx, move |setting, _| {
            setting.base_keymap = Some(keymap_base.into());
        });

        telemetry::event!("Welcome Keymap Changed", keymap = keymap_base);
    }
}

fn render_vim_mode_switch(tab_index: &mut isize, cx: &mut App) -> impl IntoElement {
    let toggle_state = if VimModeSetting::get_global(cx).0 {
        ui::ToggleState::Selected
    } else {
        ui::ToggleState::Unselected
    };
    SwitchField::new(
        "onboarding-vim-mode",
        Some("Vim Mode"),
        Some("Coming from Neovim? Use our first-class implementation of Vim Mode".into()),
        toggle_state,
        {
            let fs = <dyn Fs>::global(cx);
            move |&selection, _, cx| {
                let vim_mode = match selection {
                    ToggleState::Selected => true,
                    ToggleState::Unselected => false,
                    ToggleState::Indeterminate => {
                        return;
                    }
                };
                update_settings_file(fs.clone(), cx, move |setting, _| {
                    setting.vim_mode = Some(vim_mode);
                });

                telemetry::event!(
                    "Welcome Vim Mode Toggled",
                    options = if vim_mode { "on" } else { "off" },
                );
            }
        },
    )
    .tab_index({
        *tab_index += 1;
        *tab_index - 1
    })
}

fn render_worktree_auto_trust_switch(tab_index: &mut isize, cx: &mut App) -> impl IntoElement {
    let toggle_state = if ProjectSettings::get_global(cx).session.trust_all_worktrees {
        ui::ToggleState::Selected
    } else {
        ui::ToggleState::Unselected
    };

    let tooltip_description = "Katalyst can only allow services like language servers, project settings, and MCP servers to run after you mark a new project as trusted.";

    SwitchField::new(
        "onboarding-auto-trust-worktrees",
        Some("Trust All Projects By Default"),
        Some(
            "Automatically mark all new projects as trusted to unlock all Katalyst features".into(),
        ),
        toggle_state,
        {
            let fs = <dyn Fs>::global(cx);
            move |&selection, _, cx| {
                let trust = match selection {
                    ToggleState::Selected => true,
                    ToggleState::Unselected => false,
                    ToggleState::Indeterminate => {
                        return;
                    }
                };
                update_settings_file(fs.clone(), cx, move |setting, _| {
                    setting.session.get_or_insert_default().trust_all_worktrees = Some(trust);
                });

                telemetry::event!(
                    "Welcome Page Worktree Auto Trust Toggled",
                    options = if trust { "on" } else { "off" }
                );
            }
        },
    )
    .tab_index({
        *tab_index += 1;
        *tab_index - 1
    })
    .tooltip(Tooltip::text(tooltip_description))
}

fn render_setting_import_button(
    tab_index: isize,
    label: SharedString,
    action: &dyn Action,
    imported: bool,
) -> impl IntoElement + 'static {
    let action = action.boxed_clone();

    Button::new(label.clone(), label.clone())
        .style(ButtonStyle::OutlinedGhost)
        .size(ButtonSize::Medium)
        .label_size(LabelSize::Small)
        .selected_style(ButtonStyle::Tinted(TintColor::Accent))
        .toggle_state(imported)
        .tab_index(tab_index)
        .when(imported, |this| {
            this.end_icon(Icon::new(IconName::Check).size(IconSize::Small))
                .color(Color::Success)
        })
        .on_click(move |_, window, cx| {
            telemetry::event!("Welcome Import Settings", import_source = label,);
            window.dispatch_action(action.boxed_clone(), cx);
        })
}

fn render_import_settings_section(tab_index: &mut isize, cx: &mut App) -> impl IntoElement {
    let import_state = SettingsImportState::global(cx);
    let imports: [(SharedString, &dyn Action, bool); 2] = [
        (
            "VS Code".into(),
            &ImportVsCodeSettings { skip_prompt: false },
            import_state.vscode,
        ),
        (
            "Cursor".into(),
            &ImportCursorSettings { skip_prompt: false },
            import_state.cursor,
        ),
    ];

    let [vscode, cursor] = imports.map(|(label, action, imported)| {
        *tab_index += 1;
        render_setting_import_button(*tab_index - 1, label, action, imported)
    });

    h_flex()
        .gap_2()
        .flex_wrap()
        .justify_between()
        .child(
            v_flex()
                .gap_0p5()
                .max_w_5_6()
                .child(Label::new("Import Settings"))
                .child(
                    Label::new("Automatically pull your settings from other editors")
                        .color(Color::Muted),
                ),
        )
        .child(h_flex().gap_1().child(vscode).child(cursor))
}

pub(crate) fn session_sync_command() -> Option<PathBuf> {
    let mut candidates = Vec::new();
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            candidates.push(parent.join("katalyst-session-sync"));
            candidates.push(parent.join("../Resources/bin/katalyst-session-sync"));
        }
    }
    if let Some(home) = std::env::var_os("HOME") {
        let home = PathBuf::from(home);
        candidates.push(home.join(".local/bin/katalyst-session-sync"));
        candidates.push(home.join(".katalyst/bin/katalyst-session-sync"));
    }
    candidates.into_iter().find(|path| path.is_file())
}

pub(crate) fn session_sync_output_for_onboarding(
    args: &[&str],
) -> Result<std::process::Output, String> {
    let Some(command) = session_sync_command() else {
        return Err("Session sync helper is not installed. Re-run the Katalyst installer.".into());
    };
    std::process::Command::new(command)
        .args(args)
        .output()
        .map_err(|error| format!("Could not start session sync: {error}"))
}

fn parse_sync_output(output: std::process::Output) -> Result<serde_json::Value, String> {
    let value = serde_json::from_slice::<serde_json::Value>(&output.stdout);
    if !output.status.success() {
        if let Ok(value) = &value {
            if value.get("failed").and_then(|v| v.as_u64()).unwrap_or(0) > 0 {
                return Err(format_sync_result(value));
            }
        }
        // Do not put raw stderr (which can contain source transcript content) in the UI.
        return Err(format!(
            "Session sync failed ({}). Retry with Sync now.",
            output.status
        ));
    }
    value.map_err(|_| "Session sync returned an unreadable result. Retry with Sync now.".into())
}

fn count(value: &serde_json::Value, key: &str) -> u64 {
    value.get(key).and_then(|v| v.as_u64()).unwrap_or(0)
}

fn format_sync_result(value: &serde_json::Value) -> String {
    let sources = &value["detected_by_source"];
    format!(
        "Found {} Cursor and {} Codex chats; {} imported, {} updated, {} unchanged, {} continued in OMP, {} failed.",
        count(sources, "cursor"),
        count(sources, "codex"),
        count(value, "imported"),
        count(value, "updated"),
        count(value, "unchanged"),
        count(value, "owned_by_omp"),
        count(value, "failed"),
    )
}

pub(crate) fn sync_sessions_for_onboarding() -> Result<String, String> {
    let output = session_sync_output_for_onboarding(&[
        "sync",
        "--sources",
        "cursor,codex",
        "--all",
        "--json",
    ])?;
    parse_sync_output(output).map(|value| format_sync_result(&value))
}

pub(crate) fn session_sync_status() -> Result<String, String> {
    // Status is cached; a read-only dry run discovers chats on first installation too.
    let discovery = parse_sync_output(session_sync_output_for_onboarding(&[
        "sync",
        "--sources",
        "cursor,codex",
        "--dry-run",
        "--json",
    ])?)?;
    let status = parse_sync_output(session_sync_output_for_onboarding(&["status", "--json"])?)?;
    let sources = &discovery["detected_by_source"];
    Ok(format!(
        "Found {} Cursor and {} Codex chats; {} already imported, {} failed in the last sync.",
        count(sources, "cursor"),
        count(sources, "codex"),
        count(&status, "imported"),
        count(&status["lastResult"], "failed")
    ))
}

pub(crate) fn detect_omp() -> bool {
    let mut candidates = vec![
        PathBuf::from("/opt/homebrew/bin/omp"),
        PathBuf::from("/usr/local/bin/omp"),
    ];
    if let Some(home) = std::env::var_os("HOME") {
        let home = PathBuf::from(home);
        candidates.push(home.join(".local/bin/omp"));
        candidates.push(home.join(".bun/bin/omp"));
    }
    if let Some(path) = std::env::var_os("PATH") {
        candidates.extend(std::env::split_paths(&path).map(|directory| directory.join("omp")));
    }
    candidates.iter().any(|path| path.is_file())
}

fn session_sync_auto_marker() -> std::path::PathBuf {
    std::env::var_os("HOME")
        .map(std::path::PathBuf::from)
        .unwrap_or_default()
        .join(".katalyst/imports/auto-sync-disabled")
}

pub(crate) fn session_sync_auto_enabled() -> bool {
    !session_sync_auto_marker().exists()
}

fn set_session_sync_auto_enabled(enabled: bool) -> std::io::Result<()> {
    let marker = session_sync_auto_marker();
    if enabled {
        match std::fs::remove_file(marker) {
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
            result => result,
        }
    } else {
        if let Some(parent) = marker.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(marker, b"disabled\n")
    }
}

fn render_session_import_section(
    sync_status: SharedString,
    sync_in_progress: bool,
    auto_enabled: bool,
    cx: &mut Context<Onboarding>,
) -> impl IntoElement {
    v_flex()
        .gap_2()
        .child(
            h_flex()
                .w_full()
                .justify_between()
                .gap_2()
                .child(
                    v_flex()
                        .gap_0p5()
                        .child(Label::new("Cursor & Codex Chat Migration"))
                        .child(
                            Label::new(sync_status)
                                .size(LabelSize::Small)
                                .color(Color::Muted),
                        )
                        .child(
                            Label::new("One-way sync keeps source transcripts read-only. Continued OMP chats are never overwritten.")
                                .size(LabelSize::XSmall)
                                .color(Color::Muted),
                        ),
                )
                .child(h_flex().gap_1().child(
                    Button::new(
                        "katalyst-session-auto-import",
                        if auto_enabled { "Auto import: On" } else { "Auto import: Off" },
                    )
                        .style(ButtonStyle::Outlined)
                        .toggle_state(auto_enabled)
                        .on_click(cx.listener(|this, _, _, cx| {
                            let enabled = !this.session_sync_auto_enabled;
                            match set_session_sync_auto_enabled(enabled) {
                                Ok(()) => this.session_sync_auto_enabled = enabled,
                                Err(_) => this.session_sync_status = "Could not save the auto-import preference. Check access to ~/.katalyst/imports.".into(),
                            }
                            cx.notify();
                        })),
                ).child(
                    Button::new(
                        "katalyst-session-sync",
                        if sync_in_progress { "Syncing…" } else { "Sync now" },
                    )
                        .style(ButtonStyle::Outlined)
                        .disabled(sync_in_progress)
                        .on_click(cx.listener(|this, _, window, cx| {
                            this.sync_sessions(false, window, cx);
                        })),
                )),
        )
}

pub(crate) const FEATURED_AGENT_IDS: &[&str] =
    &["claude-acp", "codex-acp", "github-copilot-cli", "cursor"];

fn render_registry_agent_button(
    agent: &RegistryAgent,
    installed: bool,
    cx: &mut App,
) -> impl IntoElement {
    let agent_id = agent.id().to_string();
    let element_id = format!("{}-onboarding", agent_id);

    let icon = match agent.icon_path() {
        Some(icon_path) => Icon::from_external_svg(icon_path.clone()),
        None => Icon::new(IconName::Sparkle),
    }
    .size(IconSize::XSmall)
    .color(Color::Muted);

    let fs = <dyn Fs>::global(cx);

    let state_element = if installed {
        Icon::new(IconName::Check)
            .size(IconSize::Small)
            .color(Color::Success)
            .into_any_element()
    } else {
        Label::new("Install")
            .size(LabelSize::XSmall)
            .color(Color::Muted)
            .into_any_element()
    };

    AgentSetupButton::new(element_id)
        .icon(icon)
        .name(agent.name().clone())
        .state(state_element)
        .disabled(installed)
        .on_click(move |_, window, cx| {
            telemetry::event!("Welcome Agent Install Clicked", agent = agent_id.as_str());
            update_settings_file(fs.clone(), cx, {
                let agent_id = agent_id.clone();
                move |settings, _| {
                    let agent_servers = settings.agent_servers.get_or_insert_default();
                    agent_servers.entry(agent_id).or_insert_with(|| {
                        CustomAgentServerSettings::Registry {
                            env: Default::default(),
                            default_mode: None,
                            default_config_options: HashMap::default(),
                            favorite_config_option_values: HashMap::default(),
                        }
                    });
                }
            });
            window.dispatch_action(
                Box::new(zed_actions::agent::SelectAgent {
                    agent: agent_id.clone(),
                }),
                cx,
            );
        })
}

fn render_zed_agent_button(user_store: &Entity<UserStore>, cx: &mut App) -> impl IntoElement {
    let client = Client::global(cx);
    let status = *client.status().borrow();

    let plan = user_store.read(cx).plan();
    let is_free = matches!(plan, Some(Plan::ZedFree) | None);
    let is_pro = matches!(plan, Some(Plan::ZedPro));
    let is_trial = matches!(plan, Some(Plan::ZedProTrial));

    let is_signed_out = status.is_signed_out()
        || matches!(
            status,
            client::Status::AuthenticationError | client::Status::ConnectionError
        );
    let is_signing_in = status.is_signing_in();
    let is_signed_in = !is_signed_out;

    let state_element = if is_signed_out {
        Label::new("Sign In")
            .size(LabelSize::XSmall)
            .color(Color::Muted)
            .into_any_element()
    } else if is_signing_in {
        Label::new("Signing In…")
            .size(LabelSize::XSmall)
            .color(Color::Muted)
            .with_animation(
                "signing-in",
                Animation::new(Duration::from_secs(2))
                    .repeat()
                    .with_easing(pulsating_between(0.4, 0.8)),
                |label, delta| label.alpha(delta),
            )
            .into_any_element()
    } else if is_signed_in && is_free {
        Label::new("Start Free Trial")
            .size(LabelSize::XSmall)
            .color(Color::Muted)
            .into_any_element()
    } else {
        Icon::new(IconName::Check)
            .size(IconSize::Small)
            .color(Color::Success)
            .into_any_element()
    };

    AgentSetupButton::new("zed-agent-onboarding")
        .icon(
            Icon::new(IconName::ZedAgent)
                .size(IconSize::XSmall)
                .color(Color::Muted),
        )
        .name("Native Zed Agent")
        .state(state_element)
        .disabled(is_trial || is_pro)
        .map(|this| {
            if is_signed_in && is_free {
                this.on_click(move |_, _window, cx| {
                    telemetry::event!("Start Trial Clicked", state = "post-sign-in");
                    cx.open_url(&zed_urls::start_trial_url(cx))
                })
            } else {
                this.on_click(move |_, _, cx| {
                    telemetry::event!("Welcome Native Agent Sign In Clicked");
                    let client = Client::global(cx);
                    cx.spawn(async move |cx| client.sign_in_with_optional_connect(true, cx).await)
                        .detach_and_log_err(cx);
                })
            }
        })
}

fn render_omp_agent_button(installed: Option<bool>) -> impl IntoElement {
    AgentSetupButton::new("omp-agent-onboarding")
        .icon(
            Icon::new(IconName::Sparkle)
                .size(IconSize::XSmall)
                .color(Color::Accent),
        )
        .name("OMP (Default)")
        .state(
            Label::new(match installed {
                Some(true) => "Detected",
                Some(false) => "Setup guide",
                None => "Checking…",
            })
            .size(LabelSize::XSmall)
            .into_any_element(),
        )
        .disabled(installed != Some(false))
        .on_click(|_, _, cx| cx.open_url("https://github.com/Envy-7z/katalyst#installation"))
}

fn render_ai_section(
    user_store: &Entity<UserStore>,
    omp_installed: Option<bool>,
    cx: &mut App,
) -> impl IntoElement {
    let registry_agents = AgentRegistryStore::try_global(cx)
        .map(|store| store.read(cx).agents().to_vec())
        .unwrap_or_default();

    let installed_agents = cx
        .global::<SettingsStore>()
        .get::<AllAgentServersSettings>(None)
        .clone();

    let column_count = 3;

    let grid = FEATURED_AGENT_IDS.iter().fold(
        div()
            .w_full()
            .mt_1p5()
            .grid()
            .grid_cols(column_count)
            .gap_2()
            .child(render_omp_agent_button(omp_installed))
            .child(render_zed_agent_button(user_store, cx)),
        |grid, agent_id| {
            let Some(agent) = registry_agents
                .iter()
                .find(|a| a.id().as_ref() == *agent_id)
            else {
                return grid;
            };
            let is_installed = installed_agents.contains_key(*agent_id);
            grid.child(render_registry_agent_button(agent, is_installed, cx))
        },
    );

    v_flex()
        .gap_0p5()
        .child(Label::new("Katalyst Agent Setup"))
        .child(
            Label::new("OMP is the default agent. Install it with the Katalyst installer; other agents are optional.")
                .color(Color::Muted),
        )
        .child(grid)
}

pub(crate) fn render_basics_page(
    user_store: &Entity<UserStore>,
    sync_status: SharedString,
    sync_in_progress: bool,
    auto_enabled: bool,
    omp_installed: Option<bool>,
    cx: &mut Context<Onboarding>,
) -> impl IntoElement {
    let mut tab_index = 0;

    v_flex()
        .id("basics-page")
        .gap_6()
        .child(render_theme_section(&mut tab_index, cx))
        .child(render_base_keymap_section(&mut tab_index, cx))
        .child(render_ai_section(user_store, omp_installed, cx))
        .child(render_import_settings_section(&mut tab_index, cx))
        .child(render_session_import_section(
            sync_status,
            sync_in_progress,
            auto_enabled,
            cx,
        ))
        .child(render_vim_mode_switch(&mut tab_index, cx))
        .child(render_worktree_auto_trust_switch(&mut tab_index, cx))
        .child(Divider::horizontal().color(ui::DividerColor::BorderVariant))
}

#[cfg(test)]
mod session_sync_tests {
    use super::*;

    #[test]
    fn sync_result_uses_per_source_counts_and_reports_failures() {
        let result = format_sync_result(&serde_json::json!({
            "detected": 7, "detected_by_source": {"cursor": 3, "codex": 4},
            "imported": 2, "updated": 1, "unchanged": 2, "owned_by_omp": 1, "failed": 1
        }));
        assert_eq!(
            result,
            "Found 3 Cursor and 4 Codex chats; 2 imported, 1 updated, 2 unchanged, 1 continued in OMP, 1 failed."
        );
    }

    #[test]
    fn unknown_or_missing_count_fields_do_not_panic() {
        assert!(
            format_sync_result(&serde_json::json!({"new_field": true}))
                .contains("0 Cursor and 0 Codex")
        );
        assert_eq!(
            count(&serde_json::json!({"imported": "unknown"}), "imported"),
            0
        );
    }
}
