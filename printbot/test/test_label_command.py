from unittest.mock import AsyncMock, MagicMock

from printbot.bot import make_handle_label_callback, make_handle_label_command
from printbot.config import Config, PrintConfig, QlapiConfig, TelegramConfig
from printbot.label_render import Orientation


def make_config(allowed_user_ids=(111,)) -> Config:
    return Config(
        telegram=TelegramConfig(token="x", allowed_user_ids=list(allowed_user_ids)),
        qlapi=QlapiConfig(),
        print=PrintConfig(),
    )


def make_update_and_context(user_id, text):
    message = MagicMock()
    message.text = text
    message.reply_text = AsyncMock(return_value=MagicMock(edit_text=AsyncMock()))
    message.reply_photo = AsyncMock()

    update = MagicMock()
    update.effective_message = message
    update.effective_user = MagicMock(id=user_id)
    return update, message


async def test_label_no_text_replies_usage_and_no_photo():
    config = make_config()
    handler = make_handle_label_command(config)
    update, message = make_update_and_context(111, "/label   ")

    await handler(update, MagicMock())

    message.reply_text.assert_awaited_once_with("Usage: /label <text>")
    message.reply_photo.assert_not_called()


async def test_label_unauthorized_rejected():
    config = make_config(allowed_user_ids=[111])
    handler = make_handle_label_command(config)
    update, message = make_update_and_context(999, "/label hi")

    await handler(update, MagicMock())

    message.reply_text.assert_awaited_once_with("You're not authorized to use this bot.")
    message.reply_photo.assert_not_called()


async def test_label_authorized_reply_photo_and_state():
    config = make_config()
    handler = make_handle_label_command(config)
    update, message = make_update_and_context(111, "/label hello")
    context = MagicMock()
    context.chat_data = {}

    await handler(update, context)

    message.reply_photo.assert_awaited_once()
    state = context.chat_data["label_preview"]
    assert state["text"] == "hello"
    assert state["orientation"] is Orientation.WIDTH_FIXED
    assert "id" in state


async def test_label_cancel_clears_state_and_edits_caption():
    config = make_config()
    client = MagicMock()
    client.submit_job = AsyncMock()
    handler = make_handle_label_callback(config, client)

    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_caption = AsyncMock()
    preview_id = "abc12345"
    query.data = f"label:{preview_id}:cancel"
    context = MagicMock()
    context.chat_data = {
        "label_preview": {
            "id": preview_id,
            "text": "hi",
            "orientation": Orientation.WIDTH_FIXED,
            "font_size": 64,
        }
    }

    await handler(MagicMock(callback_query=query, effective_user=MagicMock(id=111)), context)

    assert "label_preview" not in context.chat_data
    query.edit_message_caption.assert_awaited_once_with(caption="❌ Cancelled")
    client.submit_job.assert_not_called()


async def test_label_print_calls_submit_with_rotate_and_clears_state():
    config = make_config()
    client = MagicMock()
    client.submit_job = AsyncMock(return_value="job-1")
    client.get_job_status = AsyncMock(return_value={"status": "done"})
    handler = make_handle_label_callback(config, client)

    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_caption = AsyncMock()
    preview_id = "abc12345"
    query.data = f"label:{preview_id}:print"
    context = MagicMock()
    context.chat_data = {
        "label_preview": {
            "id": preview_id,
            "text": "hi",
            "orientation": Orientation.HEIGHT_FIXED,
            "font_size": 64,
        }
    }

    await handler(MagicMock(callback_query=query, effective_user=MagicMock(id=111)), context)

    assert "label_preview" not in context.chat_data
    client.submit_job.assert_awaited_once()
    kwargs = client.submit_job.await_args.kwargs
    assert kwargs["rotate"] is True  # HEIGHT_FIXED -> rotate
    assert kwargs["copies"] == 1


async def test_label_stale_preview_answers_alert_and_no_client():
    config = make_config()
    client = MagicMock()
    client.submit_job = AsyncMock()
    handler = make_handle_label_callback(config, client)

    query = MagicMock()
    query.answer = AsyncMock()
    query.edit_message_caption = AsyncMock()
    query.data = "label:other123:print"
    context = MagicMock()
    context.chat_data = {
        "label_preview": {
            "id": "stale123",
            "text": "hi",
            "orientation": Orientation.WIDTH_FIXED,
            "font_size": 64,
        }
    }

    await handler(
        MagicMock(callback_query=query, effective_user=MagicMock(id=111)), context
    )

    query.answer.assert_awaited_once()
    assert "expired" in query.answer.await_args.args[0]
    client.submit_job.assert_not_called()
