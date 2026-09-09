"""Telegram bot: send a photo or PDF, it gets printed via qlapi."""
import asyncio
import logging
from typing import Optional

from telegram import Message, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from printbot.config import Config
from printbot.qlapi_client import QlapiClient, QlapiError

logger = logging.getLogger(__name__)

# ponytail: fixed poll cadence/timeout instead of a configurable backoff --
# a label print takes a few seconds, this is generous. Bump POLL_ATTEMPTS if
# a slower printer needs it.
POLL_INTERVAL_SECONDS = 1.5
POLL_ATTEMPTS = 15


def _extract_file(message: Message) -> Optional[tuple]:
    """Returns (filename, telegram_file_id) for a supported attachment, or
    None if the message has nothing printable.
    """
    if message.photo:
        # Telegram always re-encodes photos as JPEG and photo sizes have no
        # filename; use the largest size.
        return "photo.jpg", message.photo[-1].file_id

    if message.document:
        name = (message.document.file_name or "").lower()
        if name.endswith((".pdf", ".jpg", ".jpeg", ".png")):
            return message.document.file_name, message.document.file_id

    return None


async def _poll_until_finished(client: QlapiClient, job_id: str) -> str:
    """Polls GET /job/{id} until done/failed or POLL_ATTEMPTS is exhausted.
    Returns a short human-readable result message.
    """
    for _ in range(POLL_ATTEMPTS):
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
        status = await client.get_job_status(job_id)
        if status["status"] == "done":
            return "✅ Printed!"
        if status["status"] == "failed":
            return f"❌ Print failed: {status.get('error') or 'unknown error'}"
    return f"⏳ Still printing (job {job_id}), check back later."


def make_handle_media(config: Config, client: QlapiClient):
    async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        user = update.effective_user

        if user is None or user.id not in config.telegram.allowed_user_ids:
            # Logged so unauthorized attempts on a physical printer leave an
            # audit trail, and so you can find your own id to bootstrap the
            # allowlist (start the bot, message it, read the id from here).
            logger.warning(
                "Rejected print request from unauthorized user id=%s",
                user.id if user else None,
            )
            await message.reply_text("You're not authorized to use this bot.")
            return

        attachment = _extract_file(message)
        if attachment is None:
            await message.reply_text("Send a photo, PDF, JPG, or PNG to print it.")
            return

        filename, file_id = attachment

        # Reply *before* downloading: Telegram rejects getFile above 20MB, and
        # without this the user would get no feedback at all on that path.
        status_message = await message.reply_text("🖨 Printing…")
        try:
            telegram_file = await context.bot.get_file(file_id)
            # bytes(), not the raw bytearray: httpx's multipart encoder only
            # special-cases str/bytes and otherwise calls .read() on it.
            content = bytes(await telegram_file.download_as_bytearray())
            job_id = await client.submit_job(
                filename, content, rotate=config.print.rotate, copies=config.print.copies
            )
            result = await _poll_until_finished(client, job_id)
        except QlapiError as exc:
            if exc.status_code == 503:
                await status_message.edit_text(f"❌ Printer is unavailable: {exc.detail}")
            else:
                await status_message.edit_text(f"❌ Could not print: {exc.detail}")
            return
        except Exception:
            # Download failure, or qlapi restarting mid-job (its job state is
            # in-memory, so polls start 404ing). Without this the status
            # message would sit at "Printing…" forever.
            logger.exception("Unexpected failure while handling a print request")
            await status_message.edit_text("❌ Something went wrong, check the logs.")
            return

        await status_message.edit_text(result)

    return handle_media


def build_application(config: Config, client: QlapiClient) -> Application:
    application = Application.builder().token(config.telegram.token).build()
    # Document.ALL rather than per-mime filters: those match on the sender's
    # declared mime type, which disagrees with _extract_file's extension check
    # (a real .pdf sent as application/octet-stream would be dropped with no
    # reply at all). One gate, in _extract_file, so rejections are explainable.
    handler = MessageHandler(
        filters.PHOTO | filters.Document.ALL,
        make_handle_media(config, client),
    )
    application.add_handler(handler)
    return application
