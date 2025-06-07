import reflex as rx


def main_table():
    return rx.fragment(
        rx.flex(
            add_customer_button(),
            rx.spacer(),
            rx.cond(
                State.sort_reverse,
                rx.icon(
                    "arrow-down-z-a",
                    size=28,
                    stroke_width=1.5,
                    cursor="pointer",
                    on_click=State.toggle_sort,
                ),
                rx.icon(
                    "arrow-down-a-z",
                    size=28,
                    stroke_width=1.5,
                    cursor="pointer",
                    on_click=State.toggle_sort,
                ),
            ),
            rx.select(
                ["name", "email", "phone", "address", "payments", "date", "status"],
                placeholder="Sort By: Name",
                size="3",
                on_change=lambda sort_value: State.sort_values(sort_value),
            ),
            rx.input(
                rx.input.slot(rx.icon("search")),
                placeholder="Search here...",
                size="3",
                max_width="225px",
                width="100%",
                variant="surface",
                on_change=lambda value: State.filter_values(value),
            ),
            justify="end",
            align="center",
            spacing="3",
            wrap="wrap",
            width="100%",
            padding_bottom="1em",
        ),
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    _header_cell("Name", "user"),
                    _header_cell("Email", "mail"),
                    _header_cell("Phone", "phone"),
                    _header_cell("Address", "home"),
                    _header_cell("Payments", "dollar-sign"),
                    _header_cell("Date", "calendar"),
                    _header_cell("Status", "truck"),
                    _header_cell("Actions", "cog"),
                ),
            ),
            rx.table.body(rx.foreach(State.users, show_customer)),
            variant="surface",
            size="3",
            width="100%",
            on_mount=State.load_entries,
        ),
    )


# def generic_table(data, headers):
#     return rx.table(
#         rx.thead(rx.tr([rx.th(h) for h in headers])),
#         rx.tbody([rx.tr([rx.td(str(getattr(row, h.lower()))) for h in headers]) for row in data]),
#     )
