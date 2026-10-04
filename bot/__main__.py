"""Run with python -m bot from the project directory."""

import logging

from bot.app import build_application
from bot.config import Settings


def main():
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    # HTTP logs can expose the Telegram token embedded in request URLs.
    for name in ("httpx", "httpcore", "openai", "telegram"):
        logging.getLogger(name).setLevel(logging.CRITICAL)
    try:
        settings = Settings.load()
    except ValueError as error:
        raise SystemExit(str(error)) from None
    try:
        build_application(settings).run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
    except Exception as error:
        raise SystemExit(
            f"Ошибка запуска: {type(error).__name__}. "
            "Проверь подключение, токены и отсутствие второй копии бота."
        ) from None


if __name__ == "__main__":
    main()
