import logging

import reflex as rx

from dashboard import styles
from dashboard.config import settings as app_settings
from dashboard.expenses import page as expenses_page  # noqa: F401
from dashboard.pages import *  # noqa: F401,F403

# Pages register themselves when their modules are imported; Reflex does not
# discover them, so these imports are required.

_app_logger = logging.getLogger("dashboard")
_app_logger.setLevel(app_settings.log_level.upper())
if not _app_logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    _app_logger.addHandler(_handler)

app = rx.App(
    style=styles.base_style,
    stylesheets=styles.base_stylesheets,
    toaster=rx.toast.provider(position="top-right"),
)
