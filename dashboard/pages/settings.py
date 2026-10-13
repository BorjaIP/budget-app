"""The settings page."""

import reflex as rx

from .. import styles
from ..components.page_header import page_header
from ..templates import template
from ..views.color_picker import primary_color_picker, secondary_color_picker
from ..views.radius_picker import radius_picker
from ..views.scaling_picker import scaling_picker


def section(title: str, description: str, control: rx.Component) -> rx.Component:
    return rx.vstack(
        rx.vstack(
            rx.heading(title, as_="h2", size="3", weight="medium"),
            rx.text(description, size="2", color=rx.color("gray", 11)),
            spacing="1",
            align="start",
        ),
        control,
        spacing="4",
        width="100%",
        padding_top="1.5rem",
        border_top=styles.border,
    )


@template(route="/settings", title="Ajustes")
def settings() -> rx.Component:
    return rx.vstack(
        page_header("Ajustes", "Apariencia de la aplicación."),
        section(
            "Color principal",
            "Acento de botones y elementos activos. El gris mantiene la interfaz neutra.",
            primary_color_picker(),
        ),
        section(
            "Color secundario",
            "Tono de grises de fondos y bordes.",
            secondary_color_picker(),
        ),
        section(
            "Radio de bordes",
            "Redondeo de botones, campos y superficies.",
            radius_picker(),
        ),
        section(
            "Escala",
            "Tamaño general de la interfaz.",
            scaling_picker(),
        ),
        spacing="6",
        width="100%",
    )
