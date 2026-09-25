use gpui::{
    App, ClipboardItem, Context, DismissEvent, EventEmitter, FocusHandle, Focusable, Window,
    prelude::*,
};
use ui::{
    Button, ButtonStyle, Color, Icon, IconName, IconSize, Label, LabelSize, Modal, ModalFooter,
    ModalHeader, Section, prelude::*,
};
use workspace::ModalView;

pub struct DiscordRemoteModal {
    focus_handle: FocusHandle,
    is_configured: bool,
    bot_token_masked: Option<String>,
    channel_id: Option<String>,
    copied_template: bool,
}

impl DiscordRemoteModal {
    pub fn new(_window: &mut Window, cx: &mut Context<Self>) -> Self {
        let (is_configured, bot_token_masked, channel_id) = Self::check_config();
        Self {
            focus_handle: cx.focus_handle(),
            is_configured,
            bot_token_masked,
            channel_id,
            copied_template: false,
        }
    }

    fn check_config() -> (bool, Option<String>, Option<String>) {
        let home = std::env::var("HOME").unwrap_or_default();
        let path = std::path::PathBuf::from(home).join(".config/zed/settings.json");
        if let Ok(content) = std::fs::read_to_string(path) {
            if let Ok(json) = serde_json::from_str::<serde_json::Value>(&content) {
                if let Some(discord) = json.get("katalyst.discord") {
                    let enabled = discord
                        .get("enabled")
                        .and_then(|v| v.as_bool())
                        .unwrap_or(false);
                    let token = discord
                        .get("bot_token")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string());
                    let channel = discord
                        .get("channel_id")
                        .and_then(|v| v.as_str())
                        .map(|s| s.to_string());

                    if enabled && token.as_ref().is_some_and(|t| !t.trim().is_empty()) {
                        let masked = token.map(|t| {
                            if t.len() > 10 {
                                format!("{}••••••••{}", &t[..4], &t[t.len() - 4..])
                            } else {
                                "••••••••".to_string()
                            }
                        });
                        return (true, masked, channel);
                    }
                }
            }
        }
        (false, None, None)
    }

    fn copy_template(&mut self, cx: &mut Context<Self>) {
        let template = r#""katalyst.discord": {
  "enabled": true,
  "bot_token": "YOUR_DISCORD_BOT_TOKEN",
  "channel_id": "YOUR_DISCORD_CHANNEL_ID",
  "authorized_user_ids": []
}"#;
        cx.write_to_clipboard(ClipboardItem::new_string(template.to_string()));
        self.copied_template = true;
        cx.notify();
    }
}

impl Focusable for DiscordRemoteModal {
    fn focus_handle(&self, _cx: &App) -> FocusHandle {
        self.focus_handle.clone()
    }
}

impl EventEmitter<DismissEvent> for DiscordRemoteModal {}
impl ModalView for DiscordRemoteModal {
    fn fade_out_background(&self) -> bool {
        true
    }
}

impl Render for DiscordRemoteModal {
    fn render(&mut self, _window: &mut Window, cx: &mut Context<Self>) -> impl IntoElement {
        let is_configured = self.is_configured;
        let token_masked = self.bot_token_masked.clone();
        let channel_id = self.channel_id.clone();
        let copied = self.copied_template;

        v_flex()
            .id("discord-remote-modal")
            .key_context("DiscordRemoteModal")
            .w(rems(38.))
            .max_w(rems(38.))
            .bg(cx.theme().colors().elevated_surface_background)
            .border_1()
            .border_color(cx.theme().colors().border)
            .rounded_xl()
            .shadow_xl()
            .overflow_hidden()
            .track_focus(&self.focus_handle)
            .on_action(cx.listener(|_, _: &menu::Cancel, _, cx| {
                cx.emit(DismissEvent);
            }))
            .child(
                Modal::new("discord-remote-modal", None)
                    .header(
                        ModalHeader::new()
                            .headline("Discord Remote Control")
                            .description(
                                "Control your Katalyst coding agent remotely from Discord on your phone or desktop. \
                                Approve plans, send instructions, and receive notifications while away from your Mac."
                            )
                            .show_dismiss_button(true),
                    )
                    .section(
                        Section::new().child(
                            v_flex()
                                .gap_3()
                                .child(
                                    h_flex()
                                        .justify_between()
                                        .items_center()
                                        .p_3()
                                        .rounded_md()
                                        .bg(cx.theme().colors().element_background)
                                        .border_1()
                                        .border_color(cx.theme().colors().border)
                                        .child(
                                            h_flex()
                                                .gap_2()
                                                .items_center()
                                                .child(
                                                    Icon::new(IconName::Chat)
                                                        .size(IconSize::Medium)
                                                        .color(if is_configured { Color::Accent } else { Color::Muted }),
                                                )
                                                .child(
                                                    v_flex()
                                                        .child(
                                                            Label::new("Bridge Status")
                                                                .size(LabelSize::Small)
                                                                .color(Color::Muted),
                                                        )
                                                        .child(
                                                            Label::new(if is_configured {
                                                                "● Active & Configured"
                                                            } else {
                                                                "● Not Configured"
                                                            })
                                                            .size(LabelSize::Default)
                                                            .color(if is_configured { Color::Success } else { Color::Warning }),
                                                        ),
                                                ),
                                        )
                                        .child(
                                            if is_configured {
                                                v_flex()
                                                    .items_end()
                                                    .gap_0p5()
                                                    .child(
                                                        Label::new(format!("Token: {}", token_masked.unwrap_or_default()))
                                                            .size(LabelSize::Small)
                                                            .color(Color::Muted),
                                                    )
                                                    .child(
                                                        Label::new(format!("Channel: {}", channel_id.unwrap_or_default()))
                                                            .size(LabelSize::Small)
                                                            .color(Color::Muted),
                                                    )
                                            } else {
                                                v_flex().child(
                                                    Label::new("Requires Bot Token & Channel")
                                                        .size(LabelSize::Small)
                                                        .color(Color::Muted),
                                                )
                                            }
                                        ),
                                )
                                .child(
                                    v_flex()
                                        .gap_1p5()
                                        .child(
                                            Label::new("How to Connect:")
                                                .size(LabelSize::Default)
                                                .color(Color::Default),
                                        )
                                        .child(
                                            v_flex()
                                                .gap_1()
                                                .p_2p5()
                                                .rounded_md()
                                                .bg(cx.theme().colors().editor_background)
                                                .border_1()
                                                .border_color(cx.theme().colors().border)
                                                .child(
                                                    Label::new("1. Create Bot in Discord Developer Portal (enable Message Content Intent)")
                                                        .size(LabelSize::Small)
                                                        .color(Color::Default),
                                                )
                                                .child(
                                                    Label::new("2. Copy your Bot Token and target Channel ID (enable Developer Mode)")
                                                        .size(LabelSize::Small)
                                                        .color(Color::Default),
                                                )
                                                .child(
                                                    Label::new("3. Add \"katalyst.discord\" block to ~/.config/zed/settings.json")
                                                        .size(LabelSize::Small)
                                                        .color(Color::Default),
                                                ),
                                        ),
                                )
                                .child(
                                    v_flex()
                                        .gap_1()
                                        .child(
                                            h_flex()
                                                .justify_between()
                                                .items_center()
                                                .child(
                                                    Label::new("Settings Template:")
                                                        .size(LabelSize::Small)
                                                        .color(Color::Muted),
                                                )
                                                .child(
                                                    Button::new("copy-template-btn", if copied { "Copied!" } else { "Copy Template" })
                                                        .style(ButtonStyle::Subtle)
                                                        .on_click(cx.listener(|this, _, _, cx| {
                                                            this.copy_template(cx);
                                                        })),
                                                ),
                                        )
                                        .child(
                                            v_flex()
                                                .p_2p5()
                                                .rounded_md()
                                                .bg(cx.theme().colors().editor_background)
                                                .border_1()
                                                .border_color(cx.theme().colors().border)
                                                .child(
                                                    Label::new(
                                                        "\"katalyst.discord\": {\n  \"enabled\": true,\n  \"bot_token\": \"YOUR_BOT_TOKEN\",\n  \"channel_id\": \"YOUR_CHANNEL_ID\"\n}"
                                                    )
                                                    .size(LabelSize::Small)
                                                    .color(Color::Muted),
                                                ),
                                        ),
                                )
                                .child(
                                    v_flex()
                                        .gap_1()
                                        .child(
                                            Label::new("Supported Remote Commands:")
                                                .size(LabelSize::Small)
                                                .color(Color::Muted),
                                        )
                                        .child(
                                            h_flex()
                                                .gap_2()
                                                .child(Label::new("/approve").size(LabelSize::Small).color(Color::Accent))
                                                .child(Label::new("•").size(LabelSize::Small).color(Color::Muted))
                                                .child(Label::new("/continue").size(LabelSize::Small).color(Color::Accent))
                                                .child(Label::new("•").size(LabelSize::Small).color(Color::Muted))
                                                .child(Label::new("/status").size(LabelSize::Small).color(Color::Accent))
                                                .child(Label::new("•").size(LabelSize::Small).color(Color::Muted))
                                                .child(Label::new("/abort").size(LabelSize::Small).color(Color::Accent)),
                                        ),
                                ),
                        ),
                    )
                    .footer(
                        ModalFooter::new()
                            .end_slot(
                                h_flex()
                                    .gap_2()
                                    .child(
                                        Button::new("open-settings-btn", "Edit in settings.json")
                                            .style(ButtonStyle::Filled)
                                            .on_click(cx.listener(|_, _, window, cx| {
                                                window.dispatch_action(Box::new(zed_actions::OpenSettings), cx);
                                                cx.emit(DismissEvent);
                                            })),
                                    )
                                    .child(
                                        Button::new("close-btn", "Close")
                                            .style(ButtonStyle::Subtle)
                                            .on_click(cx.listener(|_, _, _, cx| {
                                                cx.emit(DismissEvent);
                                            })),
                                    ),
                            ),
                    ),
            )
    }
}
