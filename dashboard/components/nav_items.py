"""Primary navigation destinations shared by the sidebar and the mobile bottom bar."""

import reflex as rx

NAV_ITEMS = [
    ("/", "Resumen", "home"),
    ("/transactions", "Transacciones", "receipt"),
    ("/budgets", "Presupuestos", "pie-chart"),
    ("/comparison", "Comparativa", "calendar-range"),
    ("/settings", "Ajustes", "settings"),
]


def is_active(href: str):
    """Whether the current route is `href`; the home route reports an empty or index path."""
    path = rx.State.router.page.path
    if href == "/":
        return rx.Var.create(["/", "", "/index"]).contains(path)
    return path == href
