import os

import reflex as rx
from reflex.plugins import RadixThemesPlugin, SitemapPlugin

# Keep uploads inside data/ for every run mode (read lazily by rx.get_upload_dir()).
os.environ.setdefault("REFLEX_UPLOADED_FILES_DIR", "data/uploaded_files")

config = rx.Config(
    app_name="dashboard",
    plugins=[RadixThemesPlugin()],
    disable_plugins=[SitemapPlugin],
    show_built_with_reflex=False,  # no sticky "Built with Reflex" badge in production
)
