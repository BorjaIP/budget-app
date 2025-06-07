import reflex as rx

def summary_chart(data):
    return rx.chart(
        type="bar",
        data={
            "labels": [d["month"] for d in data],
            "datasets": [
                {"label": "Income", "data": [d["income"] for d in data]},
                {"label": "Expenses", "data": [d["expense"] for d in data]}
            ]
        }
    )
