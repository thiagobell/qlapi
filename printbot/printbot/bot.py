"""Telegram bot: send a photo or PDF, it gets printed via qlapi."""
import asyncio
import logging
import re
import uuid
from typing import Optional

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Message,
    Update,
)
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from printbot.config import Config
from printbot.label_render import (
    DEFAULT_FONT_SIZE,
    FONT_SIZE_STEP,
    MAX_FONT_SIZE,
    MIN_FONT_SIZE,
    Orientation,
    render_label,
    to_png_bytes,
)
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


def _is_authorized(config: Config, user) -> bool:
    return user is not None and user.id in config.telegram.allowed_user_ids


def make_handle_media(config: Config, client: QlapiClient):
    async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        message = update.effective_message
        user = update.effective_user

        if not _is_authorized(config, user):
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


def _label_caption(orientation: Orientation, font_size: int, shrunk: bool) -> str:
    caption = f"Orientation: {orientation.description}\nFont size: {font_size}pt"
    if shrunk:
        caption += "\n⚠️ Font size auto-reduced to fit 62mm."
    return caption


def _label_keyboard(preview_id: str) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("↕️ Switch orientation", callback_data=f"label:{preview_id}:orientation")],
        [
            InlineKeyboardButton("➖ Smaller", callback_data=f"label:{preview_id}:font-"),
            InlineKeyboardButton("➕ Bigger", callback_data=f"label:{preview_id}:font+"),
        ],
        [
            InlineKeyboardButton("🖨 Print", callback_data=f"label:{preview_id}:print"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"label:{preview_id}:cancel"),
        ],
    ]
    return InlineKeyboardMarkup(rows)


def make_handle_label_command(config: Config):
    async def handle_label_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.effective_user
        if not _is_authorized(config, user):
            logger.warning(
                "Rejected /label from unauthorized user id=%s",
                user.id if user else None,
            )
            await update.effective_message.reply_text("You're not authorized to use this bot.")
            return

        text = update.effective_message.text or ""
        m = re.match(r"^/label(?:@\w+)?\s?(.*)$", text, re.DOTALL)
        extracted = m.group(1) if m else ""
        if not extracted.strip():
            await update.effective_message.reply_text("Usage: /label <text>")
            return

        orientation = Orientation.WIDTH_FIXED
        font_size = DEFAULT_FONT_SIZE
        preview = render_label(extracted, orientation, font_size)
        preview_id = uuid.uuid4().hex[:8]
        context.chat_data["label_preview"] = {
            "id": preview_id,
            "text": extracted,
            "orientation": orientation,
            "font_size": font_size,
        }
        await update.effective_message.reply_photo(
            photo=to_png_bytes(preview.image),
            caption=_label_caption(orientation, preview.font_size, preview.shrunk),
            reply_markup=_label_keyboard(preview_id),
        )

    return handle_label_command


def make_handle_label_callback(config: Config, client: QlapiClient):
    async def handle_label_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        if not _is_authorized(config, update.effective_user):
            await query.answer("You're not authorized.", show_alert=True)
            return

        try:
            _, preview_id, action = query.data.split(":", maxsplit=2)
        except ValueError:
            await query.answer("This preview expired, send /label again.", show_alert=True)
            return

        state = context.chat_data.get("label_preview")
        if state is None or state["id"] != preview_id:
            await query.answer("This preview expired, send /label again.", show_alert=True)
            return

        await query.answer()

        def rerender():
            return render_label(state["text"], state["orientation"], state["font_size"])

        if action == "cancel":
            context.chat_data.pop("label_preview", None)
            await query.edit_message_caption(caption="❌ Cancelled")
            return

        if action == "orientation":
            state["orientation"] = state["orientation"].other
        elif action == "font-":
            state["font_size"] = max(MIN_FONT_SIZE, state["font_size"] - FONT_SIZE_STEP)
        elif action == "font+":
            state["font_size"] = min(MAX_FONT_SIZE, state["font_size"] + FONT_SIZE_STEP)

        if action in ("orientation", "font-", "font+"):
            preview = rerender()
            await query.edit_message_media(
                media=InputMediaPhoto(
                    media=to_png_bytes(preview.image),
                    # preview.font_size, not state's: HEIGHT_FIXED may have
                    # auto-shrunk, and the caption should name what was drawn.
                    caption=_label_caption(state["orientation"], preview.font_size, preview.shrunk),
                ),
                reply_markup=_label_keyboard(preview_id),
            )
            return

        if action == "print":
            context.chat_data.pop("label_preview", None)
            preview = render_label(state["text"], state["orientation"], state["font_size"])
            rotate = state["orientation"].rotate
            await query.edit_message_caption(caption="🖨 Printing…")
            try:
                job_id = await client.submit_job(
                    "label.png", to_png_bytes(preview.image), rotate=rotate, copies=config.print.copies
                )
                result = await _poll_until_finished(client, job_id)
            except QlapiError as exc:
                if exc.status_code == 503:
                    await query.edit_message_caption(caption=f"❌ Printer is unavailable: {exc.detail}")
                else:
                    await query.edit_message_caption(caption=f"❌ Could not print: {exc.detail}")
                return
            except Exception:
                logger.exception("Unexpected failure while printing a label")
                await query.edit_message_caption(caption="❌ Something went wrong, check the logs.")
                return
            await query.edit_message_caption(caption=result)

    return handle_label_callback


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
    application.add_handler(CommandHandler("label", make_handle_label_command(config)))
    application.add_handler(
        CallbackQueryHandler(make_handle_label_callback(config, client), pattern=r"^label:")
    )
    return application
