import reflex as rx

from dashboard.components.page_header import page_header
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


@template(route="/expenses", title="Gastos", on_load=TableState.load_entries_from_database)
def expenses() -> rx.Component:
    return rx.vstack(
        page_header(
            "Gastos",
            actions=rx.hstack(
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
                    "Recategorizar",
                    variant="soft",
                    color_scheme="gray",
                    size="2",
                    on_click=TableState.force_recategorize,
                    disabled=TableState.is_categorizing,
                ),
                spacing="3",
                align="center",
            ),
        ),
        main_table(),
        rx.script(_SLASH_FOCUS),
        spacing="5",
        width="100%",
    )
