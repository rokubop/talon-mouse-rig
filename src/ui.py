from talon import actions, cron

def show_reloading_notification():
    """Show brief 'Reloading...' notification before files are touched"""
    try:
        def reloading_ui():
            screen, div, text = actions.user.ui_elements(["screen", "div", "text"])
            return screen(align_items="flex_end", justify_content="flex_end")[
                div(
                    padding=15,
                    margin=50,
                    background_color="#0088ffdd",
                    border_radius=10
                )[
                    text("Reloading...", font_size=20, color="white", font_weight="bold")
                ]
            ]

        actions.user.ui_elements_show(reloading_ui)

        def hide_notification():
            actions.user.ui_elements_hide(reloading_ui)

        # Hide after brief flash (will be destroyed by reload anyway)
        cron.after("500ms", hide_notification)
    except (AttributeError, ImportError):
        # ui_elements not available, silently skip
        pass
