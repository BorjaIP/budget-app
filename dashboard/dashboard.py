import reflex as rx

from dashboard import styles
from dashboard.expenses import page as expenses_page  # noqa: F401
from dashboard.pages import *  # noqa: F401,F403

# Pages register themselves when their modules are imported; Reflex does not
# discover them, so these imports are required.

app = rx.App(
    style=styles.base_style,
    stylesheets=styles.base_stylesheets,
    toaster=rx.toast.provider(position="top-right"),
)
