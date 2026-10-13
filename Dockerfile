FROM python:3.12-slim

# Reflex needs Node.js/npm on the host to build and run its frontend (bun/npm
# bootstrap happens the same way it would on a local dev machine).
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates unzip \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# uv manages the Python environment/lockfile for this project.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

COPY pyproject.toml uv.lock rxconfig.py ./
COPY dashboard/ ./dashboard/
COPY assets/ ./assets/

RUN uv sync --frozen --no-dev

# Let reflex bootstrap its own frontend deps (bun cache, node modules) on
# first run, same as local dev — simplest path that actually works for a
# personal, single-user deployment.
RUN uv run reflex init

EXPOSE 3000 8000

CMD ["uv", "run", "reflex", "run", "--env", "prod", "--backend-host", "0.0.0.0"]
