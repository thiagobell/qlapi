FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Install dependencies first, in their own layer, so they're cached across
# rebuilds that only change application code.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY printbot printbot
RUN uv sync --frozen --no-dev

ENV PATH="/app/.venv/bin:$PATH"

# config.yaml is bind-mounted at runtime (see docker-compose.yml) -- never
# baked into the image, it holds the bot token.
CMD ["python", "-m", "printbot"]
