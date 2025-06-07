import reflex as rx


def app_layout(content):
    return rx.vstack(
        rx.hstack(
            rx.link("Summary", href="/"),
            rx.link("Expenses", href="/expenses"),
            rx.link("Incomes", href="/incomes"),
            spacing="4",
        ),
        rx.box(content, width="100%"),
    )
