import os

import reflex as rx

# Keep uploads inside data/ for every run mode (read lazily by rx.get_upload_dir()).
os.environ.setdefault("REFLEX_UPLOADED_FILES_DIR", "data/uploaded_files")

config = rx.Config(
    app_name="dashboard",
)
