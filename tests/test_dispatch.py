"""Exercise real Telegram update dispatch without a network connection."""

import unittest
import warnings
from unittest.mock import AsyncMock, patch

from telegram import Update, User
from telegram.ext import ExtBot
from telegram.request import HTTPXRequest
from test_bot import fixture

from bot.app import build_application
from bot.config import Settings


class DispatchTests(unittest.IsolatedAsyncioTestCase):
    async def test_quiz_through_conversation_handler(self):
        _, _, ai = fixture()
        with (
            warnings.catch_warnings(),
            patch.object(HTTPXRequest, "_build_client"),
        ):
            warnings.simplefilter("ignore", category=UserWarning)
            app = build_application(Settings("123:TEST", "unused"), ai=ai)
        app.bot._bot_user = User(123, "Test", True, username="test_bot")
        app._initialized = True
        sender = {"id": 42, "is_bot": False, "first_name": "Test"}
        chat = {"id": 42, "type": "private"}

        def message(number, text, command=False):
            data = {
                "message_id": number,
                "date": 0,
                "chat": chat,
                "from": sender,
                "text": text,
            }
            if command:
                data["entities"] = [
                    {"type": "bot_command", "offset": 0, "length": len(text)}
                ]
            return Update.de_json(
                {"update_id": number, "message": data}, app.bot
            )

        with (
            patch.object(ExtBot, "send_message", new_callable=AsyncMock),
            patch.object(ExtBot, "send_photo", new_callable=AsyncMock),
            patch.object(
                ExtBot, "answer_callback_query", new_callable=AsyncMock
            ),
        ):
            await app.process_update(message(1, "/quiz", command=True))
            data = app.user_data[42]["session"]
            self.assertEqual(data["mode"], "quiz")
            query = Update.de_json(
                {
                    "update_id": 2,
                    "callback_query": {
                        "id": "query-1",
                        "from": sender,
                        "chat_instance": "test",
                        "data": f"{data['nonce']}|topic:science",
                        "message": {
                            "message_id": 10,
                            "date": 0,
                            "chat": chat,
                            "from": {
                                "id": 123,
                                "first_name": "Test",
                                "is_bot": True,
                            },
                            "text": "Choose topic",
                        },
                    },
                },
                app.bot,
            )
            await app.process_update(query)
            self.assertIn("question", data)
            await app.process_update(message(3, "4"))
            self.assertEqual(data["correct"], 1)
            await app.process_update(message(4, "/start", command=True))
            self.assertEqual(app.user_data[42]["session"]["mode"], "menu")
