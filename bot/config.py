"""Load secrets from environment without including them in diagnostics."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    telegram_token: str = field(repr=False)
    openai_key: str = field(repr=False)
    model: str = "gpt-5.6-luna"
    reasoning_effort: str | None = None
    allowed_ids: frozenset[int] = frozenset()

    @classmethod
    def load(cls):
        load_dotenv(ROOT / ".env")
        names = ("TELEGRAM_BOT_TOKEN", "OPENAI_API_KEY")
        missing = [name for name in names if not os.getenv(name, "").strip()]
        if missing:
            raise ValueError("Заполните .env: " + ", ".join(missing))
        try:
            allowed = frozenset(
                int(value.strip())
                for value in os.getenv("ALLOWED_USER_IDS", "").split(",")
                if value.strip()
            )
        except ValueError:
            raise ValueError(
                "ALLOWED_USER_IDS: нужны числа через запятую"
            ) from None
        effort = os.getenv("OPENAI_REASONING_EFFORT", "").strip().lower() or None
        valid_efforts = {"none", "minimal", "low", "medium", "high", "xhigh", "max"}
        if effort not in valid_efforts and effort is not None:
            raise ValueError(
                "OPENAI_REASONING_EFFORT: use none, minimal, low, medium, "
                "high, xhigh, max, or leave it empty"
            )
        return cls(
            telegram_token=os.environ[names[0]].strip(),
            openai_key=os.environ[names[1]].strip(),
            model=os.getenv("OPENAI_MODEL", "gpt-5.6-luna").strip(),
            reasoning_effort=effort,
            allowed_ids=allowed,
        )
