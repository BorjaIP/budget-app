import reflex as rx

from .. import styles
from .nav_items import NAV_ITEMS, is_active


def _item(href: str, label: str, icon: str) -> rx.Component:
    active = is_active(href)
    return rx.link(
        rx.vstack(
            rx.icon(icon, size=20),
            rx.text(label, size="1"),
            spacing="1",
            align="center",
        ),
        href=href,
        underline="none",
        flex="1",
        padding_y="0.5em",
        text_align="center",
        color=rx.cond(active, rx.color("gray", 12), rx.color("gray", 11)),
        font_weight=rx.cond(active, "500", "400"),
        border_top=rx.cond(active, "2px solid var(--gray-12)", "2px solid transparent"),
        custom_attrs={"aria-current": rx.cond(active, "page", "false")},
    )


def bottom_nav() -> rx.Component:
    return rx.box(
        rx.hstack(
            *[_item(href, label, icon) for href, label, icon in NAV_ITEMS],
            width="100%",
            spacing="0",
            justify="center",
        ),
        display=["block", "block", "none", "none", "none"],
        position="fixed",
        bottom="0",
        left="0",
        right="0",
        z_index="20",
        background_color=rx.color("gray", 1),
        border_top=styles.border,
        padding="0 0.5em env(safe-area-inset-bottom, 0)",
    )
