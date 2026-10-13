"""The "Reglas" tab of Ajustes: what the app has learned from the user's corrections."""

import reflex as rx

from dashboard.components.card import card
from dashboard.components.icon import icon
from dashboard.rules_state import RuleRow, RulesState

_NOTE = {"overflow": "hidden", "text_overflow": "ellipsis", "white_space": "nowrap"}


def _new_rule_form() -> rx.Component:
    return card(
        rx.vstack(
            rx.text(
                "Cuando el concepto contenga el nombre de un comercio, se categoriza así. "
                "Lo que corriges a mano crea reglas automáticamente.",
                size="2",
                color=rx.color("gray", 11),
            ),
            rx.flex(
                rx.input(
                    value=RulesState.new_text,
                    on_change=RulesState.set_new_text,
                    placeholder="Comercio, por ejemplo Mercadona",
                    size="2",
                    max_length=80,
                    flex="2",
                    min_width="14rem",
                    custom_attrs={"aria-label": "Comercio de la regla"},
                ),
                rx.select(
                    RulesState.category_options,
                    value=RulesState.new_category,
                    on_change=RulesState.set_new_category,
                    size="2",
                    custom_attrs={"aria-label": "Categoría de la regla"},
                ),
                rx.select(
                    RulesState.new_sub_options,
                    value=RulesState.new_subcategory,
                    on_change=RulesState.set_new_subcategory,
                    size="2",
                    custom_attrs={"aria-label": "Subcategoría de la regla"},
                ),
                rx.button(
                    "Crear regla",
                    size="2",
                    color_scheme="gray",
                    high_contrast=True,
                    disabled=RulesState.new_text == "",
                    on_click=RulesState.create_rule,
                ),
                gap="0.75rem",
                wrap="wrap",
                align="center",
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        title="Nueva regla",
    )


def _rule_row(rule: RuleRow) -> rx.Component:
    return rx.flex(
        rx.vstack(
            rx.text(rule.example, size="2", weight="medium", style=_NOTE, max_width="100%"),
            rx.text(rule.confirmations_text, size="1", color=rx.color("gray", 11)),
            spacing="0",
            align="start",
            flex="1",
            min_width="0",
        ),
        rx.badge(
            rx.cond(rule.subcategory != "", rule.category + " · " + rule.subcategory, rule.category),
            color_scheme=rule.color,
            variant="soft",
            size="1",
        ),
        rx.hstack(
            rx.button("Editar", variant="ghost", color_scheme="gray", size="2", on_click=RulesState.open_edit(rule.key)),
            rx.button("Borrar", variant="ghost", color_scheme="red", size="2", on_click=RulesState.open_delete(rule.key)),
            spacing="3",
        ),
        align="center",
        gap="0.75rem",
        wrap="wrap",
        padding_y="0.65rem",
        border_bottom=f"1px solid {rx.color('gray', 4, True)}",
        width="100%",
    )


def _edit_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Editar regla"),
            rx.dialog.description(
                rx.text("Comercio: ", rx.text.strong(RulesState.edit_example), size="2"),
            ),
            rx.vstack(
                rx.text("Categoría", size="2", weight="medium"),
                rx.select(RulesState.category_options, value=RulesState.edit_category,
                          on_change=RulesState.set_edit_category, size="2", width="100%"),
                rx.text("Subcategoría", size="2", weight="medium"),
                rx.select(RulesState.edit_sub_options, value=RulesState.edit_subcategory,
                          on_change=RulesState.set_edit_subcategory, size="2", width="100%"),
                rx.text(
                    "Al guardar, los movimientos de este comercio que no hayas categorizado a mano pasan a esta categoría.",
                    size="1",
                    color=rx.color("gray", 11),
                ),
                spacing="2",
                width="100%",
                margin_top="1rem",
            ),
            rx.flex(
                rx.dialog.close(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                rx.button("Guardar", color_scheme="gray", high_contrast=True, on_click=RulesState.save_edit),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            max_width="460px",
        ),
        open=RulesState.show_edit,
        on_open_change=RulesState.set_show_edit,
    )


def _delete_dialog() -> rx.Component:
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Borrar regla"),
            rx.alert_dialog.description(
                "Se dejará de aplicar la regla de «" + RulesState.delete_example + "». Los movimientos que había "
                "categorizado vuelven a revisión; los que categorizaste a mano no cambian."
            ),
            rx.flex(
                rx.alert_dialog.cancel(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                rx.alert_dialog.action(rx.button("Borrar", color_scheme="red", on_click=RulesState.confirm_delete)),
                spacing="3",
                margin_top="1rem",
                justify="end",
            ),
            max_width="460px",
        ),
        open=RulesState.show_delete,
        on_open_change=RulesState.set_show_delete,
    )


def rules_panel() -> rx.Component:
    return rx.vstack(
        _new_rule_form(),
        card(
            rx.vstack(
                rx.hstack(
                    rx.input(
                        rx.input.slot(icon("search", size=16)),
                        value=RulesState.search,
                        on_change=RulesState.set_search,
                        placeholder="Buscar regla",
                        size="2",
                        max_width="22rem",
                        custom_attrs={"aria-label": "Buscar regla"},
                    ),
                    rx.spacer(),
                    rx.text(RulesState.rules_summary, size="1", color=rx.color("gray", 11)),
                    width="100%",
                    align="center",
                    wrap="wrap",
                ),
                rx.vstack(rx.foreach(RulesState.visible_rules, _rule_row), spacing="0", width="100%"),
                spacing="3",
                width="100%",
            ),
            title="Reglas aprendidas",
        ),
        _edit_dialog(),
        _delete_dialog(),
        spacing="4",
        width="100%",
    )
