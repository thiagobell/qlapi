# printbot

Telegram bot front-end for [`qlapi`](../qlapi/README.md). Send a photo, PDF, JPG, or PNG in a
chat and it gets printed, or use `/label <text>` to print text as a label. Long-polls Telegram, no
inbound webhook/port needed.

## `/label <text>`

Renders the text onto 62mm continuous tape as a preview with buttons to adjust it before
anything prints:

- Multi-line messages create hard line breaks (each line stays on its own row).
- `↕️ Switch orientation` toggles between width-fixed (default) and height-fixed layouts.
- `➖ Smaller` / `➕ Bigger` adjust the font size.
- `🖨 Print` sends it to the printer; `❌ Cancel` discards the preview.

Nothing is sent to the printer until `🖨 Print` is tapped.

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
