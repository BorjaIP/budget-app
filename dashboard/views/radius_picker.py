import reflex as rx

from ..templates.template import ThemeState

_OPTIONS = [
    ("none", "Ninguno"),
    ("small", "Pequeño"),
    ("medium", "Medio"),
    ("large", "Grande"),
    ("full", "Completo"),
]


def radius_picker() -> rx.Component:
    return rx.select.root(
        rx.select.trigger(custom_attrs={"aria-label": "Radio de bordes"}),
        rx.select.content(
            *[rx.select.item(label, value=value) for value, label in _OPTIONS],
        ),
        size="2",
        value=ThemeState.radius,
        on_change=ThemeState.set_radius,
    )
