from unittest.mock import AsyncMock, MagicMock

from printbot.bot import _extract_file, make_handle_media
from printbot.config import Config, PrintConfig, QlapiConfig, TelegramConfig
from printbot.qlapi_client import QlapiError


def make_config(allowed_user_ids=(111,)) -> Config:
    return Config(
        telegram=TelegramConfig(token="x", allowed_user_ids=list(allowed_user_ids)),
        qlapi=QlapiConfig(),
        print=PrintConfig(),
    )


def test_extract_file_picks_largest_photo():
    small = MagicMock(file_id="small")
    large = MagicMock(file_id="large")
    message = MagicMock(photo=[small, large], document=None)

    assert _extract_file(message) == ("photo.jpg", "large")


def test_extract_file_accepts_pdf_document():
    doc = MagicMock(file_name="label.pdf", file_id="doc-1")
    message = MagicMock(photo=[], document=doc)

    assert _extract_file(message) == ("label.pdf", "doc-1")


def test_extract_file_rejects_unsupported_document():
    doc = MagicMock(file_name="notes.docx", file_id="doc-1")
    message = MagicMock(photo=[], document=doc)

    assert _extract_file(message) is None


def test_extract_file_none_when_no_attachment():
    message = MagicMock(photo=[], document=None)

    assert _extract_file(message) is None


def make_update_and_context(user_id, photo=(), document=None):
    message = MagicMock()
    message.photo = list(photo)
    message.document = document
    message.reply_text = AsyncMock(return_value=MagicMock(edit_text=AsyncMock()))

    update = MagicMock()
    update.effective_message = message
    update.effective_user = MagicMock(id=user_id)

    context = MagicMock()
    context.bot.get_file = AsyncMock(
        return_value=MagicMock(download_as_bytearray=AsyncMock(return_value=bytearray(b"data")))
    )
    return update, context


async def test_handler_rejects_unauthorized_user():
    config = make_config(allowed_user_ids=[111])
    client = MagicMock()
    client.submit_job = AsyncMock()
    handler = make_handle_media(config, client)

    update, context = make_update_and_context(user_id=999, photo=[MagicMock(file_id="p1")])

    await handler(update, context)

    update.effective_message.reply_text.assert_awaited_once_with(
        "You're not authorized to use this bot."
    )
    client.submit_job.assert_not_called()


async def test_handler_reports_printer_unavailable():
    config = make_config(allowed_user_ids=[111])
    client = MagicMock()
    client.submit_job = AsyncMock(side_effect=QlapiError(503, "No USB printer detected"))
    handler = make_handle_media(config, client)

    update, context = make_update_and_context(user_id=111, photo=[MagicMock(file_id="p1")])

    await handler(update, context)

    # reply_text's return value is the "status" message we later edit_text() on
    sent = update.effective_message.reply_text.return_value
    sent.edit_text.assert_awaited_once()
    assert "unavailable" in sent.edit_text.await_args.args[0]


async def test_handler_reports_qlapi_unreachable():
    """qlapi being down entirely (not just 503) must still reach the user
    rather than leaving the status message stuck on "Printing...".
    """
    config = make_config(allowed_user_ids=[111])
    client = MagicMock()
    client.submit_job = AsyncMock(
        side_effect=QlapiError(0, "qlapi unreachable: [Errno 111] Connection refused")
    )
    handler = make_handle_media(config, client)

    update, context = make_update_and_context(user_id=111, photo=[MagicMock(file_id="p1")])

    await handler(update, context)

    sent = update.effective_message.reply_text.return_value
    sent.edit_text.assert_awaited_once()
    assert "Could not print" in sent.edit_text.await_args.args[0]


async def test_handler_reports_unexpected_failure():
    """A download blowing up (e.g. Telegram's 20MB getFile limit) must not
    leave the user with no feedback.
    """
    config = make_config(allowed_user_ids=[111])
    client = MagicMock()
    client.submit_job = AsyncMock()
    handler = make_handle_media(config, client)

    update, context = make_update_and_context(user_id=111, photo=[MagicMock(file_id="p1")])
    context.bot.get_file = AsyncMock(side_effect=RuntimeError("file is too big"))

    await handler(update, context)

    sent = update.effective_message.reply_text.return_value
    sent.edit_text.assert_awaited_once()
    assert "went wrong" in sent.edit_text.await_args.args[0]
    client.submit_job.assert_not_called()
