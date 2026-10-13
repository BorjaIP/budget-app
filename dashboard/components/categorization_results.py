"""Global pieces of the categorization run: a progress strip on every page and the results dialog."""

import reflex as rx

from dashboard.components.category_badge import category_badge
from dashboard.expenses.model import Item
from dashboard.expenses.state import TableState


def categorization_banner() -> rx.Component:
    """Progress strip shown on every page while the background categorization runs."""
    return rx.cond(
        TableState.is_categorizing,
        rx.hstack(
            rx.spinner(size="1"),
            rx.vstack(
                rx.text(TableState.categorization_label, size="2"),
                rx.progress(value=TableState.categorization_progress_pct, max=100, size="1"),
                spacing="1",
                width="100%",
            ),
            rx.link("Ver transacciones", href="/transactions", size="2", underline="always", white_space="nowrap"),
            align="center",
            spacing="3",
            width="100%",
            padding="0.6rem 0.9rem",
            border=f"1px solid {rx.color('violet', 6)}",
            border_radius="var(--radius-3)",
            background=rx.color("violet", 2),
            custom_attrs={"role": "status", "aria-live": "polite"},
        ),
    )


def _line(label: str, value, note: str | None = None) -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(label, size="2"),
            rx.cond(note is not None, rx.text(note or "", size="1", color=rx.color("gray", 11)), rx.fragment()),
            spacing="0",
            align="start",
        ),
        rx.spacer(),
        rx.text(value, size="2", weight="medium", class_name="num"),
        width="100%",
        align="start",
    )


def _review_row(item: Item) -> rx.Component:
    return rx.flex(
        rx.vstack(
            rx.text(item.concept, size="2", weight="medium", style={"overflow_wrap": "anywhere"}),
            rx.text(
                item.operation_date_human
                + " · "
                + item.amount_fmt
                + rx.cond(item.repeat_count > 1, " · " + item.repeat_count.to_string() + " movimientos", ""),
                size="1",
                color=rx.color("gray", 11),
                class_name="num",
            ),
            spacing="1",
            align="start",
            flex="1",
            min_width="0",
        ),
        category_badge(item),
        rx.button(
            "Está bien",
            variant="soft",
            color_scheme="gray",
            size="1",
            on_click=TableState.confirm_review_item(item.id),
        ),
        align="center",
        gap="0.75rem",
        wrap="wrap",
        padding_y="0.6rem",
        border_bottom=f"1px solid {rx.color('gray', 4, True)}",
        width="100%",
    )


def results_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.dialog.title("Resultado de la categorización"),
            rx.dialog.description(
                "Así se ha categorizado cada movimiento y cuánta confianza tiene el modelo en sus respuestas.",
                size="2",
            ),
            rx.vstack(
                _line("Movimientos categorizados", TableState.results_total),
                _line("Por tu memoria", TableState.results_memory, "Comercios que ya habías corregido"),
                _line("Por similitud", TableState.results_similar, "Casi idénticos a uno que ya etiquetaste"),
                _line("Modelo, confianza alta", TableState.results_high, "90 % o más"),
                _line("Modelo, confianza media", TableState.results_mid),
                _line("Modelo, dudosos", TableState.results_low, "Por debajo del umbral de revisión"),
                _line("Confianza media del modelo", TableState.results_average),
                spacing="2",
                width="100%",
                margin_top="1rem",
            ),
            rx.cond(
                TableState.review_items.length() > 0,
                rx.vstack(
                    rx.heading("Revisa estos movimientos", size="3", margin_top="1.25rem"),
                    rx.text(
                        "Corrige la categoría pulsando la etiqueta, o confirma que está bien. "
                        "Lo que confirmes o corrijas se recuerda para ese comercio.",
                        size="2",
                        color=rx.color("gray", 11),
                    ),
                    rx.scroll_area(
                        rx.vstack(rx.foreach(TableState.review_items, _review_row), spacing="0", width="100%"),
                        type="auto",
                        scrollbars="vertical",
                        style={"max_height": "40vh"},
                    ),
                    spacing="2",
                    width="100%",
                    align="start",
                ),
                rx.text(
                    "No hay movimientos dudosos en esta tanda.",
                    size="2",
                    color=rx.color("gray", 11),
                    margin_top="1rem",
                ),
            ),
            rx.flex(
                rx.dialog.close(rx.button("Cerrar", variant="soft", color_scheme="gray")),
                rx.button(
                    "Ver pendientes en Transacciones",
                    color_scheme="gray",
                    high_contrast=True,
                    on_click=[TableState.set_show_results(False), TableState.drill_down_review, rx.redirect("/transactions")],
                ),
                spacing="3",
                margin_top="1rem",
                justify="end",
                wrap="wrap",
            ),
            max_width=["95vw", "95vw", "640px"],
            style={"max_height": "90vh", "overflow_y": "auto"},
        ),
        open=TableState.show_results,
        on_open_change=TableState.set_show_results,
    )
