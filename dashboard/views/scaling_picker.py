import reflex as rx

from ..templates.template import ThemeState


def scaling_picker() -> rx.Component:
    return rx.select.root(
        rx.select.trigger(custom_attrs={"aria-label": "Escala de la interfaz"}),
        rx.select.content(
            *[rx.select.item(scale, value=scale) for scale in ("90%", "95%", "100%", "105%", "110%")],
        ),
        size="2",
        value=ThemeState.scaling,
        on_change=ThemeState.set_scaling,
    )
