from collections import defaultdict
from datetime import datetime

import reflex as rx

from budget_app.components.charts import summary_chart
from budget_app.components.layout import app_layout
from budget_app.services.expense_service import get_all_expenses
from budget_app.services.income_service import get_all_incomes


def page():
    expenses = get_all_expenses()
    incomes = get_all_incomes()
    summary = defaultdict(lambda: {"income": 0, "expense": 0})

    for e in expenses:
        key = datetime.strptime(str(e.date), "%Y-%m-%d").strftime("%Y-%m")
        summary[key]["expense"] += e.amount

    for i in incomes:
        key = datetime.strptime(str(i.date), "%Y-%m-%d").strftime("%Y-%m")
        summary[key]["income"] += i.amount

    summary_data = [
        {"month": k, "income": v["income"], "expense": v["expense"]}
        for k, v in sorted(summary.items())
    ]

    return app_layout(rx.vstack(rx.heading("Summary"), summary_chart(summary_data)))
