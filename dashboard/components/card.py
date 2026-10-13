"""Flat surface used for every grouped block: hairline border, no shadow."""

import reflex as rx

from dashboard import styles


def card(*children, title: str | None = None, **props) -> rx.Component:
    header = (
        [
            rx.heading(
                title,
                as_="h2",
                size="2",
                weight="medium",
                color=rx.color("gray", 11),
                margin_bottom="1rem",
            )
        ]
        if title
        else []
    )
    return rx.box(
        *header,
        *children,
        width="100%",
        min_width="0",
        padding=["1rem", "1.25rem", "1.5rem"],
        border=styles.border,
        border_radius="var(--radius-4)",
        background="var(--color-panel-solid)",
        **props,
    )
