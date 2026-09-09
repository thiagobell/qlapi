# printbot

Telegram bot front-end for [`qlapi`](../qlapi/README.md). Send a photo, PDF, JPG, or PNG in a
chat and it gets printed. Long-polls Telegram, no inbound webhook/port needed.

## Configuration

All settings live in one YAML file (gitignored, since it holds your bot token):

```bash
cp config.example.yaml config.yaml
```

Then fill in:
- `telegram.token` — from [@BotFather](https://t.me/BotFather).
- `telegram.allowed_user_ids` — numeric Telegram user ids allowed to print. Required and
  non-empty; there is no "allow everyone" option since this triggers a real physical print.
  Send `/start` to [@userinfobot](https://t.me/userinfobot) to find your own id.
- `qlapi.base_url` — where the qlapi service is reachable. Defaults to `http://qlapi:80`, which
  resolves correctly when both services run together via the top-level `docker-compose.yml`.

## Running locally

```bash
uv run python -m printbot
```

Exits with an error message (not a crash) if `config.yaml` is missing or invalid.

## Running the tests

```bash
uv run pytest
```
