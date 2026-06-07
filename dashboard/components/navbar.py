"""Mobile-only top header with logo, page title and color-mode toggle."""

import reflex as rx

from .. import styles


def navbar() -> rx.Component:
    return rx.el.nav(
        rx.hstack(
            rx.hstack(
                rx.icon("wallet", size=20, color=rx.color("teal", 9)),
                rx.heading("Mi Presupuesto", size="3", weight="bold"),
                align="center",
                spacing="2",
            ),
            rx.spacer(),
            rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
            align="center",
            width="100%",
            padding_y="0.75em",
            padding_x=["1em", "1em", "2em"],
        ),
        display=["block", "block", "none", "none", "none"],
        position="sticky",
        top="0px",
        z_index="5",
        background_color=rx.color("gray", 1),
        border_bottom=styles.border,
    )
