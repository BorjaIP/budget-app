import reflex as rx

from dashboard import styles
from dashboard.expenses import page as expenses_page
from dashboard.pages import *

# Import all the pages.
__all__ = ["expenses_page"]


# Create the app.
app = rx.App(
    style=styles.base_style,  # type: ignore
    stylesheets=styles.base_stylesheets,
)
