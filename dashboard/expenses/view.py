import reflex as rx

from dashboard.expenses.state import Item, TableState


class TableView:

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
            rx.table.cell(
                rx.text(
                    f"€{item.amount}",
                    color=rx.cond(
                        item.amount.contains("-"),
                        rx.color("red", 11),
                        rx.color("green", 11),
                    ),
                    weight="medium",
                ),
            ),
            rx.table.cell(item.salary),
            style={"_hover": {"bg": hover_color}, "bg": bg_color},
            align="center",
        )

    def _pagination_view(self):
        return (
            rx.hstack(
                rx.text(
                    "Página ",
                    rx.code(TableState.page_number),
                    " de ",
                    rx.code(TableState.total_pages),
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

    def _upload_modal(self) -> rx.Component:
        return rx.dialog.root(
            rx.dialog.content(
                rx.dialog.title("Subir Archivo Excel"),
                rx.dialog.description(
                    "Selecciona un archivo de exportación bancaria (.xls o .xlsx) para importar gastos.",
                    size="2",
                    margin_bottom="16px",
                ),
                rx.vstack(
                    rx.upload(
                        rx.vstack(
                            rx.icon("upload", size=32, color="gray"),
                            rx.text(
                                rx.cond(
                                    TableState.is_uploading,
                                    "Procesando archivo...",
                                    "Arrastra un archivo Excel aquí o haz clic para seleccionar",
                                ),
                                size="2",
                                text_align="center",
                            ),
                            rx.foreach(
                                rx.selected_files("upload-excel"),
                                lambda f: rx.hstack(
                                    rx.icon("file-spreadsheet", size=16, color="blue"),
                                    rx.text(f, size="2", weight="medium", color="blue"),
                                    align="center",
                                    spacing="2",
                                ),
                            ),
                            align="center",
                            spacing="2",
                        ),
                        id="upload-excel",
                        multiple=False,
                        accept={
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                            "application/vnd.ms-excel": [".xls"],
                        },
                        max_files=1,
                        border="2px dashed #ccc",
                        padding="2em",
                        border_radius="8px",
                        width="100%",
                        min_height="120px",
                        display="flex",
                        align_items="center",
                        justify_content="center",
                        cursor="pointer",
                        _hover={"border_color": "blue.500"},
                    ),
                    rx.cond(
                        TableState.upload_status != "",
                        rx.callout.root(
                            rx.callout.text(TableState.upload_status),
                            color_scheme=rx.cond(
                                TableState.upload_status.startswith("❌"),
                                "red",
                                "green",
                            ),
                            width="100%",
                        ),
                    ),
                    rx.text(
                        TableState.get_upload_stats,
                        size="1",
                        color="gray",
                    ),
                    spacing="4",
                    width="100%",
                ),
                rx.flex(
                    rx.dialog.close(
                        rx.button(
                            "Cerrar",
                            variant="soft",
                            color_scheme="gray",
                        ),
                    ),
                    rx.button(
                        rx.cond(
                            TableState.is_uploading,
                            rx.spinner(size="1"),
                            rx.icon("upload", size=18),
                        ),
                        "Procesar Archivo",
                        size="3",
                        variant="solid",
                        color_scheme="blue",
                        cursor="pointer",
                        on_click=TableState.handle_upload(  # type: ignore
                            rx.upload_files(upload_id="upload-excel")
                        ),
                        disabled=TableState.is_uploading,
                    ),
                    spacing="3",
                    margin_top="16px",
                    justify="end",
                    width="100%",
                ),
                max_width="480px",
            ),
            open=TableState.show_upload_modal,
            on_open_change=TableState.set_show_upload_modal,  # type: ignore
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
                        placeholder="Ordenar por: ",
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
                        placeholder="Buscar...",
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
                rx.hstack(
                    rx.button(
                        rx.icon("upload", size=18),
                        "Subir Archivo",
                        size="3",
                        variant="solid",
                        color_scheme="blue",
                        cursor="pointer",
                        on_click=TableState.open_upload_modal,  # type: ignore
                    ),
                    rx.button(
                        rx.icon("refresh-cw", size=18),
                        "Actualizar",
                        size="3",
                        variant="outline",
                        cursor="pointer",
                        on_click=TableState.load_entries_from_database,  # type: ignore
                    ),
                    spacing="3",
                    align="center",
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
            self._upload_modal(),
            rx.text(
                "Mostrando ",
                rx.text.strong(TableState.filtered_count),
                " de ",
                rx.text.strong(TableState.total_items),
                " gastos",
                size="2",
                color=rx.color("gray", 10),
                margin_bottom="0.5em",
            ),
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
