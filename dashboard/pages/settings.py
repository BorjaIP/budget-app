"""Settings: the categories and subcategories that tag movements and guide the model."""

import reflex as rx

from ..components.card import card
from ..components.icon import icon
from ..components.page_header import page_header
from ..rules_state import RulesState
from ..taxonomy_state import KIND_LABELS, CategoryRow, SubRow, TaxonomyState
from ..views.rules_panel import rules_panel
from ..templates import template


def _note(text, size: str = "2") -> rx.Component:
    """A description: italic and muted so it reads as an explanation, not as a name."""
    return rx.text(text, size=size, color=rx.color("gray", 11), style={"font_style": "italic"})


def _sub_chip(category: str, sub: SubRow) -> rx.Component:
    return rx.hstack(
        rx.cond(
            sub.reserved,
            rx.text(sub.name, size="2"),
            rx.el.button(
                sub.name,
                type="button",
                on_click=TaxonomyState.open_edit_subcategory(category, sub.name),
                title=rx.cond(sub.description != "", sub.description, "Editar subcategoría"),
                class_name="row-link",
                style={"width": "auto", "padding": "0 0.25rem", "font_size": "var(--font-size-2)"},
            ),
        ),
        rx.cond(sub.description != "", _note("· " + sub.description, "1"), rx.fragment()),
        rx.cond(
            sub.reserved,
            rx.fragment(),
            rx.icon_button(
                icon("x", size=12),
                variant="ghost",
                color_scheme="gray",
                size="1",
                on_click=TaxonomyState.open_delete_subcategory(category, sub.name),
                custom_attrs={"aria-label": "Borrar subcategoría " + sub.name},
            ),
        ),
        spacing="1",
        align="center",
        padding="0.125rem 0.5rem",
        border=f"1px solid {rx.color('gray', 6, True)}",
        border_radius="var(--radius-3)",
    )


def _add_subcategory_form(category: str) -> rx.Component:
    return rx.form(
        rx.el.input(type="hidden", name="category", value=category),
        rx.hstack(
            rx.input(name="name", placeholder="Nueva subcategoría", size="2", max_length=40, required=True,
                     custom_attrs={"aria-label": "Nueva subcategoría de " + category}),
            rx.button("Añadir", type="submit", size="2", variant="soft", color_scheme="gray"),
            spacing="2",
        ),
        on_submit=TaxonomyState.add_subcategory,
        reset_on_submit=True,
    )


def _category_card(row: CategoryRow) -> rx.Component:
    return card(
        rx.hstack(
            rx.badge(row.name, color_scheme=row.color, variant="soft", size="2"),
            rx.spacer(),
            rx.button("Editar", variant="ghost", color_scheme="gray", size="2",
                      on_click=TaxonomyState.open_edit_category(row.name)),
            rx.cond(
                row.reserved,
                rx.fragment(),
                rx.button("Borrar", variant="ghost", color_scheme="red", size="2",
                          on_click=TaxonomyState.open_delete_category(row.name)),
            ),
            align="center",
            spacing="3",
            wrap="wrap",
            width="100%",
        ),
        rx.cond(row.description != "", rx.box(_note(row.description), margin_top="0.5rem"), rx.fragment()),
        rx.flex(
            rx.foreach(row.subcategories, lambda sub: _sub_chip(row.name, sub)),
            wrap="wrap",
            gap="0.5rem",
            margin_top="0.75rem",
        ),
        rx.box(_add_subcategory_form(row.name), margin_top="0.75rem"),
    )


def _new_category_form() -> rx.Component:
    return card(
        rx.form(
            rx.flex(
                rx.input(name="name", placeholder="Nombre de la categoría", size="2", max_length=40, required=True,
                         flex="1", min_width="12rem", custom_attrs={"aria-label": "Nombre de la nueva categoría"}),
                rx.input(name="description", placeholder="Qué incluye (opcional, ayuda al modelo)", size="2",
                         max_length=200, flex="2", min_width="16rem",
                         custom_attrs={"aria-label": "Descripción de la nueva categoría"}),
                rx.select(list(KIND_LABELS.values()), name="kind", default_value=KIND_LABELS["expense"], size="2",
                          custom_attrs={"aria-label": "Tipo de categoría"}),
                rx.button("Añadir categoría", type="submit", size="2", color_scheme="gray", high_contrast=True),
                gap="0.75rem",
                wrap="wrap",
                align="center",
            ),
            on_submit=TaxonomyState.add_category,
            reset_on_submit=True,
        ),
        title="Nueva categoría",
    )


def _edit_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title(rx.cond(TaxonomyState.edit_kind == "category", "Editar categoría", "Editar subcategoría")),
            rx.dialog.description(
                "Si cambias el nombre, los movimientos, los comercios aprendidos y los presupuestos lo siguen.",
                size="2",
            ),
            rx.vstack(
                rx.text("Nombre", size="2", weight="medium"),
                rx.input(value=TaxonomyState.edit_name, on_change=TaxonomyState.set_edit_name, max_length=40, size="2"),
                rx.text("Qué incluye (opcional)", size="2", weight="medium"),
                rx.input(value=TaxonomyState.edit_description, on_change=TaxonomyState.set_edit_description,
                         max_length=200, size="2"),
                rx.cond(
                    TaxonomyState.edit_kind == "category",
                    rx.vstack(
                        rx.text("Tipo", size="2", weight="medium"),
                        rx.select(list(KIND_LABELS.values()), value=TaxonomyState.edit_type_label,
                                  on_change=TaxonomyState.set_edit_type_label, size="2"),
                        spacing="2",
                        width="100%",
                        align="start",
                    ),
                ),
                spacing="2",
                width="100%",
                margin_top="1rem",
            ),
            rx.flex(
                rx.dialog.close(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                rx.button("Guardar", color_scheme="gray", high_contrast=True, on_click=TaxonomyState.save_edit),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            max_width="460px",
        ),
        open=TaxonomyState.show_edit,
        on_open_change=TaxonomyState.set_show_edit,
    )


def _delete_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Borrar"),
            rx.alert_dialog.description(TaxonomyState.delete_message),
            rx.flex(
                rx.alert_dialog.cancel(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                rx.alert_dialog.action(
                    rx.button("Borrar", color_scheme="red", on_click=TaxonomyState.confirm_delete),
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            max_width="460px",
        ),
        open=TaxonomyState.show_delete,
        on_open_change=TaxonomyState.set_show_delete,
    )


def _reset_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Restaurar las categorías originales"),
            rx.alert_dialog.description(
                "Vuelves a la lista con la que empezó la app. Las categorías que hayas creado se borran y sus "
                "movimientos pasan a Otros / General; los nombres que cambiaste vuelven al original."
            ),
            rx.flex(
                rx.alert_dialog.cancel(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                rx.alert_dialog.action(
                    rx.button("Restaurar", color_scheme="red", on_click=TaxonomyState.confirm_reset),
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            max_width="460px",
        ),
        open=TaxonomyState.show_reset,
        on_open_change=TaxonomyState.set_show_reset,
    )


def _categories_tab() -> rx.Component:
    return rx.vstack(
        rx.flex(
            rx.text(
                "Una descripción corta de lo que incluye cada categoría ayuda al modelo a acertar.",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.button("Restaurar originales", variant="soft", color_scheme="gray", size="2",
                      on_click=TaxonomyState.set_show_reset(True)),
            justify="between",
            align="center",
            gap="1rem",
            wrap="wrap",
            width="100%",
        ),
        _new_category_form(),
        rx.heading("Gastos", as_="h2", size="3", weight="medium", color=rx.color("gray", 11)),
        rx.vstack(rx.foreach(TaxonomyState.expense_rows, _category_card), spacing="3", width="100%"),
        rx.heading("Ingresos", as_="h2", size="3", weight="medium", color=rx.color("gray", 11)),
        rx.text(
            "Un movimiento con importe positivo se categoriza entre las categorías de ingresos, las de ahorro y Otros.",
            size="2",
            color=rx.color("gray", 11),
        ),
        rx.vstack(rx.foreach(TaxonomyState.income_rows, _category_card), spacing="3", width="100%"),
        rx.heading("Ahorro y traspasos", as_="h2", size="3", weight="medium", color=rx.color("gray", 11)),
        rx.text(
            "Para el dinero que pasas a otras cuentas que no están en la app (y el que vuelve). Estos movimientos "
            "no cuentan como gasto ni como ingreso: se muestran aparte como traspasos a ahorro.",
            size="2",
            color=rx.color("gray", 11),
        ),
        rx.vstack(rx.foreach(TaxonomyState.saving_rows, _category_card), spacing="3", width="100%"),
        _edit_dialog(),
        _delete_dialog(),
        _reset_dialog(),
        spacing="6",
        width="100%",
    )


@template(route="/settings", title="Ajustes", on_load=RulesState.load_rules)
def settings() -> rx.Component:
    return rx.vstack(
        page_header(
            "Ajustes",
            "Las categorías con las que se etiqueta cada movimiento y lo que la app ha aprendido de tus correcciones. "
            "El modelo local usa las categorías (y sus descripciones) para categorizar.",
        ),
        rx.tabs.root(
            rx.tabs.list(
                rx.tabs.trigger("Categorías", value="categories"),
                rx.tabs.trigger("Reglas", value="rules"),
            ),
            rx.tabs.content(rx.box(_categories_tab(), padding_top="1.25rem"), value="categories"),
            rx.tabs.content(rx.box(rules_panel(), padding_top="1.25rem"), value="rules"),
            default_value="categories",
            width="100%",
        ),
        spacing="5",
        width="100%",
    )
