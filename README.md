# qlapi monorepo

Two small, independently deployed services:

- [`qlapi/`](qlapi/README.md) — REST API for Brother QL label printers.
- [`printbot/`](printbot/README.md) — Telegram bot front-end for `qlapi`: send a photo or PDF in a chat and it gets printed.

Each service has its own `pyproject.toml`, `uv.lock`, and `Dockerfile`, and is built and pushed
independently — see `.github/workflows/qlapi-ci.yml` and `.github/workflows/printbot-ci.yml`.

## Running both locally

```bash
cp printbot/config.example.yaml printbot/config.yaml   # then fill in your bot token + allowed users
docker compose up --build
```

`printbot` reaches the API over the compose network at `http://qlapi:80`, so only `qlapi`'s port is
published to the host. See each service's README for its configuration.
