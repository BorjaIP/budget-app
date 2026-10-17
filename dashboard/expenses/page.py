import reflex as rx

from dashboard.components.page_header import page_header
from dashboard.components.icon import icon
from dashboard.expenses.state import TableState
from dashboard.expenses.view import main_table
from dashboard.templates import template


# "/" jumps to the search box unless the user is already typing somewhere.
_SLASH_FOCUS = """
if (!window.__budgetSlashFocus) {
  window.__budgetSlashFocus = true;
  document.addEventListener('keydown', (e) => {
    const tag = (e.target && e.target.tagName) || '';
    if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || (e.target && e.target.isContentEditable)) return;
    const box = document.getElementById('search-input');
    if (box) { e.preventDefault(); box.focus(); }
  });
}
"""


def _recategorize_dialog() -> rx.Component:
    """Warns that a global run replaces the AI categories (hand-made ones are kept)."""
    return rx.alert_dialog.root(
        rx.alert_dialog.content(
            rx.alert_dialog.title("Recategorizar con IA"),
            rx.alert_dialog.description(
                rx.vstack(
                    rx.text(
                        "Se volverán a categorizar ",
                        rx.text.strong(TableState.recategorize_auto_count),
                        " movimientos con el modelo local y sus categorías actuales se reemplazarán.",
                        size="2",
                    ),
                    rx.text(
                        "Los ",
                        rx.text.strong(TableState.recategorize_manual_count),
                        " que has categorizado a mano se conservan. Podrás deshacerlo después.",
                        size="2",
                    ),
                    spacing="2",
                    align="start",
                ),
            ),
            rx.flex(
                rx.alert_dialog.cancel(rx.button("Cancelar", variant="soft", color_scheme="gray")),
                rx.alert_dialog.action(
                    rx.button(
                        "Recategorizar",
                        color_scheme="violet",
                        on_click=TableState.confirm_recategorize,
                    ),
                ),
                spacing="3",
                margin_top="1em",
                justify="end",
            ),
            max_width="460px",
        ),
        open=TableState.show_recategorize_dialog,
        on_open_change=TableState.set_show_recategorize_dialog,
    )


@template(route="/transactions", title="Transacciones", on_load=TableState.load_entries_from_database)
def expenses() -> rx.Component:
    return rx.vstack(
        page_header(
            "Transacciones",
            actions=rx.hstack(
                rx.cond(
                    TableState.has_results,
                    rx.button(
                        "Ver resultados",
                        variant="ghost",
                        color_scheme="gray",
                        size="2",
                        on_click=TableState.open_results,
                    ),
                ),
                rx.cond(
                    TableState.can_undo_recategorize,
                    rx.button(
                        "Deshacer",
                        variant="ghost",
                        color_scheme="gray",
                        size="2",
                        on_click=TableState.undo_recategorize,
                        disabled=TableState.is_categorizing,
                    ),
                ),
                rx.button(
                    icon("magic-wand", size=14),
                    "Recategorizar",
                    variant="soft",
                    color_scheme="violet",
                    size="2",
                    on_click=TableState.open_recategorize_dialog,
                    disabled=TableState.is_categorizing,
                ),
                _recategorize_dialog(),
                spacing="3",
                align="center",
            ),
        ),
        main_table(),
        rx.script(_SLASH_FOCUS),
        spacing="5",
        width="100%",
    )
