import reflex as rx

from .. import styles


_ITEMS = [
    ("/", "Resumen", "home"),
    ("/expenses", "Gastos", "receipt"),
    ("/settings", "Ajustes", "settings"),
]


def _item(href: str, label: str, icon: str) -> rx.Component:
    active = rx.State.router.page.path == href
    return rx.link(
        rx.vstack(
            rx.icon(icon, size=22),
            rx.text(label, size="1", weight="medium"),
            spacing="1",
            align="center",
        ),
        href=href,
        underline="none",
        flex="1",
        padding_y="0.5em",
        text_align="center",
        color=rx.cond(active, styles.accent_text_color, rx.color("gray", 11)),
        background=rx.cond(active, styles.accent_bg_color, "transparent"),
    )


def bottom_nav() -> rx.Component:
    return rx.box(
        rx.hstack(
            *[_item(href, label, icon) for href, label, icon in _ITEMS],
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
        padding="0.25em 0.5em env(safe-area-inset-bottom, 0.25em)",
    )
