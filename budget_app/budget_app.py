import reflex as rx

# from budget_app.pages import expenses, incomes, summary


@rx.page()
def index():
    return rx.center(rx.heading("Hello Reflex! 👋"))


app = rx.App(
    theme=rx.theme(appearance="dark", has_background=True, radius="large", accent_color="grass")
)
# app.add_page(expenses.page, route="/expenses", title="Expenses")
# app.add_page(incomes.page, route="/incomes", title="Incomes")
# app.add_page(summary.page, route="/", title="Summary")
# app.compile()
