import reflex as rx

from ..expenses.state import Item, TableState


class TablePage:

    def _header_cell(self, text: str, icon: str) -> rx.Component:
        return rx.table.column_header_cell(
            rx.hstack(
                rx.icon(icon, size=18),
                rx.text(text),
                align="center",
                spacing="2",
            ),
        )

    def _show_item(self, item: Item, index: int) -> rx.Component:
        bg_color = rx.cond(
            index % 2 == 0,
            rx.color("gray", 1),
            rx.color("accent", 2),
        )
        hover_color = rx.cond(
            index % 2 == 0,
            rx.color("gray", 3),
            rx.color("accent", 3),
        )
        return rx.table.row(
            rx.table.row_header_cell(item.operation_date),
            rx.table.row_header_cell(item.value_date),
            rx.table.row_header_cell(item.concept),
            rx.table.cell(f"€{item.amout}"),
            rx.table.cell(item.salary),
            style={"_hover": {"bg": hover_color}, "bg": bg_color},
            align="center",
        )

    def _pagination_view(self):
        return (
            rx.hstack(
                rx.text(
                    "Page ",
                    rx.code(TableState.page_number),
                    f" of {TableState.total_pages}",
                    justify="end",
                ),
                rx.hstack(
                    rx.icon_button(
                        rx.icon("chevrons-left", size=18),
                        on_click=TableState.first_page,  # type: ignore
                        opacity=rx.cond(TableState.page_number == 1, 0.6, 1),
                        color_scheme=rx.cond(TableState.page_number == 1, "gray", "accent"),
                        variant="soft",
                    ),
                    rx.icon_button(
                        rx.icon("chevron-left", size=18),
                        on_click=TableState.prev_page,  # type: ignore
                        opacity=rx.cond(TableState.page_number == 1, 0.6, 1),
                        color_scheme=rx.cond(TableState.page_number == 1, "gray", "accent"),
                        variant="soft",
                    ),
                    rx.icon_button(
                        rx.icon("chevron-right", size=18),
                        on_click=TableState.next_page,  # type: ignore
                        opacity=rx.cond(TableState.page_number == TableState.total_pages, 0.6, 1),
                        color_scheme=rx.cond(
                            TableState.page_number == TableState.total_pages,
                            "gray",
                            "accent",
                        ),
                        variant="soft",
                    ),
                    rx.icon_button(
                        rx.icon("chevrons-right", size=18),
                        on_click=TableState.last_page,  # type: ignore
                        opacity=rx.cond(TableState.page_number == TableState.total_pages, 0.6, 1),
                        color_scheme=rx.cond(
                            TableState.page_number == TableState.total_pages,
                            "gray",
                            "accent",
                        ),
                        variant="soft",
                    ),
                    align="center",
                    spacing="2",
                    justify="end",
                ),
                spacing="5",
                margin_top="1em",
                align="center",
                width="100%",
                justify="end",
            ),
        )

    def get_filters(self):
        return (
            rx.flex(
                rx.flex(
                    rx.cond(
                        TableState.sort_reverse,
                        rx.icon(
                            "arrow-down-z-a",
                            size=28,
                            stroke_width=1.5,
                            cursor="pointer",
                            flex_shrink="0",
                            on_click=TableState.toggle_sort,  # type: ignore
                        ),
                        rx.icon(
                            "arrow-down-a-z",
                            size=28,
                            stroke_width=1.5,
                            cursor="pointer",
                            flex_shrink="0",
                            on_click=TableState.toggle_sort,  # type: ignore
                        ),
                    ),
                    rx.select(
                        TableState.get_item_list,
                        placeholder="Sort By: ",
                        size="3",
                        on_change=TableState.set_sort_value,  # type: ignore
                    ),
                    rx.input(
                        rx.input.slot(rx.icon("search")),
                        rx.input.slot(
                            rx.icon("x"),
                            justify="end",
                            cursor="pointer",
                            on_click=TableState.setvar("search_value", ""),
                            display=rx.cond(TableState.search_value, "flex", "none"),
                        ),
                        value=TableState.search_value,
                        placeholder="Search here...",
                        size="3",
                        max_width=["150px", "150px", "200px", "250px"],
                        width="100%",
                        variant="surface",
                        color_scheme="gray",
                        on_change=TableState.set_search_value,  # type: ignore
                    ),
                    align="center",
                    justify="end",
                    spacing="3",
                ),
                spacing="3",
                justify="between",
                wrap="wrap",
                width="100%",
                padding_bottom="1em",
            ),
        )

    def get_header(self):
        return (
            rx.table.header(
                rx.table.row(
                    self._header_cell("Fecha Operación", "calendar"),
                    self._header_cell("Fecha Valor", "calendar"),
                    self._header_cell("Concepto", "notebook-pen"),
                    self._header_cell("Importe", "euro"),
                    self._header_cell("Saldo", "euro"),
                ),
            ),
        )

    def get_body(self) -> rx.Component:
        return rx.table.body(
            rx.foreach(
                TableState.get_current_page,
                lambda item, index: self._show_item(item, index),
            )
        )

    def main_table(self) -> rx.Component:
        return rx.box(
            self.get_filters(),
            rx.table.root(
                self.get_header(),
                self.get_body(),
                variant="surface",
                size="3",
                width="100%",
            ),
            self._pagination_view(),
            width="100%",
        )
