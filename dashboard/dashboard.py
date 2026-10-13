import reflex as rx

from dashboard import styles

# Reflex auto-discovers pages from dashboard/pages/ and any
# @rx.page/@template decorators found during module scanning.
# Explicit imports are kept only for side-effect registration when
# a page lives outside dashboard/pages/.


app = rx.App(
    style=styles.base_style,
    stylesheets=styles.base_stylesheets,
    toaster=rx.toast.provider(position="top-right"),
)
