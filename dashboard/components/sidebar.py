"""Desktop persistent sidebar with the wordmark and primary navigation."""

import reflex as rx

from .. import styles
from .nav_items import NAV_ITEMS, is_active


def _header() -> rx.Component:
    return rx.heading(
        "Mi presupuesto",
        size="4",
        weight="medium",
        letter_spacing="-0.01em",
        padding="0.35em 0.6em",
        margin_bottom="1em",
    )


def _footer() -> rx.Component:
    return rx.hstack(
        rx.color_mode.button(
            variant="ghost",
            color_scheme="gray",
            custom_attrs={"aria-label": "Cambiar entre modo claro y oscuro"},
        ),
        rx.spacer(),
        align="center",
        width="100%",
        padding="0.35em",
    )


def _item(href: str, label: str, icon: str) -> rx.Component:
    active = is_active(href)
    return rx.link(
        rx.hstack(
            rx.icon(icon, size=16),
            rx.text(label, size="2"),
            color=rx.cond(active, rx.color("gray", 12), styles.text_color),
            font_weight=rx.cond(active, "500", "400"),
            background_color=rx.cond(active, rx.color("gray", 4, True), "transparent"),
            style={"_hover": {"background_color": rx.color("gray", 3, True)}},
            align="center",
            border_radius=styles.border_radius,
            width="100%",
            spacing="2",
            padding="0.5em 0.6em",
        ),
        underline="none",
        href=href,
        width="100%",
        custom_attrs={"aria-current": rx.cond(active, "page", "false")},
    )


def sidebar() -> rx.Component:
    return rx.flex(
        rx.vstack(
            _header(),
            rx.vstack(
                *[_item(href, label, icon) for href, label, icon in NAV_ITEMS],
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
