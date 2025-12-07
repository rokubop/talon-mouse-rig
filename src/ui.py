from talon import actions, cron

def show_reload_notification():
    try:
        def reload_notification_ui():
            screen, div, text = actions.user.ui_elements(["screen", "div", "text"])
            return screen(align_items="flex_end", justify_content="flex_end")[
                div(
                    padding=15,
                    margin=50,
                    background_color="#00aa00dd",
                    border_radius=10
                )[
                    text("Rig reloaded!", font_size=20, color="white", font_weight="bold")
                ]
            ]

        actions.user.ui_elements_show(reload_notification_ui)

        def hide_notification():
            actions.user.ui_elements_hide(reload_notification_ui)

        cron.after("3s", hide_notification)
    except (AttributeError, ImportError):
        # ui_elements not available, silently skip
        pass
