"""Surface for every grouped block: white, rounded, hairline border and a barely visible shadow."""

import reflex as rx

from dashboard import styles


def card(*children, title: str | None = None, subtitle: str | None = None, action: rx.Component | None = None, **props) -> rx.Component:
    header = []
    if title:
        heading = rx.vstack(
            rx.heading(title, as_="h2", size="3", weight="medium", color=rx.color("gray", 12)),
            rx.text(subtitle, size="1", color=rx.color("gray", 11)) if subtitle else rx.fragment(),
            spacing="1",
            align="start",
        )
        header = [
            rx.flex(
                heading,
                action if action is not None else rx.fragment(),
                justify="between",
                align="start",
                gap="1rem",
                margin_bottom="1rem",
            )
        ]
    return rx.box(
        *header,
        *children,
        width="100%",
        min_width="0",
        padding=["1rem", "1.25rem", "1.5rem"],
        border=styles.border,
        border_radius=styles.card_radius,
        box_shadow=styles.card_shadow,
        background="var(--color-panel-solid)",
        **props,
    )
