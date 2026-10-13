"""Light/dark switch built on Radix Icons (Reflex's built-in button uses Lucide)."""

import reflex as rx

from .icon import icon


def color_mode_toggle() -> rx.Component:
    return rx.icon_button(
        rx.color_mode_cond(light=icon("moon"), dark=icon("sun")),
        on_click=rx.toggle_color_mode,
        variant="ghost",
        color_scheme="gray",
        size="2",
        cursor="pointer",
        custom_attrs={"aria-label": "Cambiar entre modo claro y oscuro"},
    )
