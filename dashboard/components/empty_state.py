import reflex as rx

from .icon import icon


def empty_state(
    glyph: str,
    title: str,
    description: str,
    action_label: str | None = None,
    on_action=None,
) -> rx.Component:
    body = [
        icon(glyph, size=20, color=rx.color("gray", 9)),
        rx.heading(title, as_="h2", size="4", weight="medium"),
        rx.text(
            description,
            size="2",
            color=rx.color("gray", 11),
            text_align="center",
            max_width="32em",
        ),
    ]
    if action_label and on_action is not None:
        body.append(
            rx.button(
                action_label,
                size="2",
                color_scheme="gray",
                high_contrast=True,
                on_click=on_action,
                margin_top="0.5em",
            )
        )

    return rx.center(
        rx.vstack(*body, spacing="2", align="center"),
        padding="4rem 1rem",
        border=f"1px dashed {rx.color('gray', 6, True)}",
        border_radius="var(--radius-4)",
        width="100%",
    )
