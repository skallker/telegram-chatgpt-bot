"""Offline behavioral tests; no real tokens or network requests."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.ai import AI
from bot.app import (
    button,
    command,
    enter_mode,
    handle_text,
    keyboard,
    menu,
    message,
    session,
    split_text,
)
from bot.config import Settings


def fixture():
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=42),
        effective_chat=SimpleNamespace(type="private"),
        effective_message=SimpleNamespace(
            reply_text=AsyncMock(), reply_photo=AsyncMock(), text="Hello"
        ),
        callback_query=None,
    )
    ai = SimpleNamespace(
        complete=AsyncMock(return_value="AI response"),
        question=AsyncMock(return_value={"question": "2 + 2?", "answer": "4"}),
        grade=AsyncMock(return_value={"correct": True, "explanation": "Да"}),
    )
    context = SimpleNamespace(
        user_data={},
        args=[],
        application=SimpleNamespace(
            bot_data={"ai": ai, "settings": Settings("unused", "unused")}
        ),
    )
    return update, context, ai


async def click(update, context, action, nonce=None):
    update.callback_query = SimpleNamespace(
        answer=AsyncMock(),
        data=f"{nonce or session(context)['nonce']}|{action}",
    )
    return await button(update, context)


class BotTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_six_modes_send_prepared_image(self):
        for mode in ("random", "gpt", "talk", "quiz", "translate", "resume"):
            with self.subTest(mode=mode):
                update, context, _ = fixture()
                await enter_mode(update, context, mode)
                update.effective_message.reply_photo.assert_awaited_once()
                self.assertEqual(session(context)["mode"], mode)

    async def test_fact_again_and_finish(self):
        update, context, ai = fixture()
        await enter_mode(update, context, "random")
        await click(update, context, "fact")
        self.assertEqual(ai.complete.await_count, 2)
        await click(update, context, "end")
        self.assertEqual(session(context)["mode"], "menu")

    async def test_quiz_counts_once_and_changes_topic(self):
        update, context, ai = fixture()
        await enter_mode(update, context, "quiz")
        await click(update, context, "topic:science")
        await handle_text(update, context, "4")
        await handle_text(update, context, "4")
        self.assertEqual(session(context)["correct"], 1)
        self.assertEqual(session(context)["total"], 1)
        ai.grade.assert_awaited_once()
        await click(update, context, "topics")
        await click(update, context, "topic:history")
        ai.grade.return_value = {"correct": False, "explanation": "Нет"}
        await handle_text(update, context, "5")
        self.assertEqual(session(context)["correct"], 1)
        self.assertEqual(session(context)["total"], 2)

    async def test_quiz_failure_preserves_question_and_score(self):
        update, context, ai = fixture()
        await enter_mode(update, context, "quiz")
        await click(update, context, "topic:science")
        ai.grade.side_effect = TimeoutError()
        await message(update, context)
        self.assertEqual(session(context)["total"], 0)
        self.assertIn("question", session(context))

    async def test_stale_buttons_cannot_change_new_mode(self):
        update, context, ai = fixture()
        await enter_mode(update, context, "random")
        old = session(context)["nonce"]
        await enter_mode(update, context, "resume")
        await click(update, context, "fact", old)
        self.assertEqual(session(context)["mode"], "resume")
        self.assertEqual(ai.complete.await_count, 1)

    async def test_separate_users_and_bounded_chat_history(self):
        update, context, _ = fixture()
        _, other, _ = fixture()
        await enter_mode(update, context, "gpt")
        for number in range(10):
            await handle_text(update, context, str(number))
        self.assertEqual(len(session(context)["history"]), 12)
        self.assertNotIn("history", session(other))
        await menu(update, context)
        self.assertNotIn("history", session(context))

    async def test_personality_prompt_and_translation_language(self):
        update, context, ai = fixture()
        await enter_mode(update, context, "talk")
        await handle_text(update, context, "hello")
        ai.complete.assert_not_awaited()
        await click(update, context, "person:curie")
        await handle_text(update, context, "hello")
        self.assertIn("Мария Кюри", ai.complete.call_args.args[0])
        await enter_mode(update, context, "translate")
        await click(update, context, "lang:uk")
        await handle_text(update, context, "hello")
        self.assertIn("Украинский", ai.complete.call_args.args[0])
        await click(update, context, "languages")
        self.assertNotIn("language", session(context))

    async def test_resume_retry_does_not_lose_last_answer(self):
        update, context, ai = fixture()
        await enter_mode(update, context, "resume")
        for answer in ("Developer", "University", "No experience"):
            await handle_text(update, context, answer)
        ai.complete.side_effect = TimeoutError()
        update.effective_message.text = "Python"
        await message(update, context)
        self.assertEqual(len(session(context)["answers"]), 3)
        ai.complete.side_effect = None
        await message(update, context)
        self.assertEqual(len(session(context)["answers"]), 4)

    async def test_gpt_inline_command(self):
        update, context, ai = fixture()
        update.effective_message.text = "/gpt Hello"
        context.args = ["Hello"]
        await command(update, context)
        self.assertEqual(ai.complete.call_args.args[1], "Hello")

    async def test_unauthorized_user_and_group_do_not_call_ai(self):
        update, context, ai = fixture()
        update.effective_message.text = "/random"
        context.application.bot_data["settings"] = Settings(
            "unused", "unused", allowed_ids=frozenset({1})
        )
        await command(update, context)
        ai.complete.assert_not_awaited()
        context.application.bot_data["settings"] = Settings("unused", "unused")
        update.effective_chat.type = "group"
        await command(update, context)
        ai.complete.assert_not_awaited()

    def test_emoji_long_messages_keep_text_and_limit(self):
        text = "😀Привет" * 2000
        chunks = list(split_text(text))
        self.assertEqual("".join(chunks), text)
        self.assertTrue(
            all(len(part.encode("utf-16-le")) // 2 <= 3500 for part in chunks)
        )

    def test_callback_data_fits_telegram_limit(self):
        _, context, _ = fixture()
        markup = keyboard(context, [("Topic", "topic:geography")])
        for row in markup.inline_keyboard:
            for item in row:
                self.assertLessEqual(len(item.callback_data.encode()), 64)


class ValidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_rejects_string_boolean_and_missing_question(self):
        ai = AI.__new__(AI)
        ai.complete = AsyncMock(
            return_value={"correct": "false", "explanation": "No"}
        )
        with self.assertRaises(ValueError):
            await ai.grade({"question": "Q", "answer": "A"}, "B")
        ai.complete.return_value = {"question": "Q"}
        with self.assertRaises(ValueError):
            await ai.question("Science")


if __name__ == "__main__":
    unittest.main()
