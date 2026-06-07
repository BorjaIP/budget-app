import reflex as rx

from .. import styles


def empty_state(
    icon: str,
    title: str,
    description: str,
    action_label: str | None = None,
    on_action=None,
) -> rx.Component:
    body = [
        rx.icon(icon, size=48, color=rx.color("gray", 8)),
        rx.heading(title, size="5", weight="medium"),
        rx.text(
            description,
            size="3",
            color=rx.color("gray", 11),
            text_align="center",
            max_width="32em",
        ),
    ]
    if action_label and on_action is not None:
        body.append(
            rx.button(
                rx.icon("upload", size=18),
                action_label,
                size="3",
                on_click=on_action,
                margin_top="0.5em",
            )
        )

    return rx.center(
        rx.vstack(*body, spacing="3", align="center"),
        padding="4em 1em",
        border=f"1px dashed {rx.color('gray', 6)}",
        border_radius=styles.border_radius,
        width="100%",
    )
