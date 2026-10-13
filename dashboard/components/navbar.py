"""Mobile-only top header with the wordmark and color-mode toggle."""

import reflex as rx

from .. import styles
from .color_mode_toggle import color_mode_toggle


def navbar() -> rx.Component:
    return rx.el.nav(
        rx.hstack(
            rx.heading("Mi presupuesto", size="3", weight="medium", letter_spacing="-0.01em"),
            rx.spacer(),
            color_mode_toggle(),
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
