"""Desktop persistent sidebar with logo and primary navigation."""

import reflex as rx

from .. import styles


_ITEMS = [
    ("/", "Resumen", "home"),
    ("/expenses", "Gastos", "receipt"),
    ("/settings", "Ajustes", "settings"),
]


def _header() -> rx.Component:
    return rx.hstack(
        rx.icon("wallet", size=24, color=rx.color("teal", 9)),
        rx.heading("Mi Presupuesto", size="4", weight="bold"),
        align="center",
        width="100%",
        padding="0.35em",
        margin_bottom="1em",
    )


def _footer() -> rx.Component:
    return rx.hstack(
        rx.color_mode.button(style={"opacity": "0.8", "scale": "0.95"}),
        rx.spacer(),
        align="center",
        width="100%",
        padding="0.35em",
    )


def _item(href: str, label: str, icon: str) -> rx.Component:
    active = rx.State.router.page.path == href
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=18),
            rx.text(label, size="3", weight="medium"),
            color=rx.cond(active, styles.accent_text_color, styles.text_color),
            background_color=rx.cond(active, styles.accent_bg_color, "transparent"),
            style={
                "_hover": {
                    "background_color": rx.cond(
                        active, styles.accent_bg_color, styles.gray_bg_color
                    ),
                },
            },
            align="center",
            border_radius=styles.border_radius,
            width="100%",
            spacing="2",
            padding="0.5em 0.6em",
        ),
        underline="none",
        href=href,
        width="100%",
    )


def sidebar() -> rx.Component:
    return rx.flex(
        rx.vstack(
            _header(),
            rx.vstack(
                *[_item(href, label, icon) for href, label, icon in _ITEMS],
                spacing="1",
                width="100%",
            ),
            rx.spacer(),
            _footer(),
            width=styles.sidebar_content_width,
            height="100dvh",
            padding="1em",
        ),
        display=["none", "none", "flex", "flex", "flex"],
        max_width=styles.sidebar_width,
        width="auto",
        height="100%",
        position="sticky",
        top="0px",
        flex="0 0 auto",
        background_color=rx.color("gray", 2),
        border_right=styles.border,
    )
