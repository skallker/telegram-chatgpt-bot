"""Generate portfolio-friendly English Telegram mode banners in memory."""

from functools import lru_cache
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1200
HEIGHT = 600

BANNERS = {
    "random": ("Random Fact", "Learn something new every day", "01 / 06"),
    "gpt": ("ChatGPT", "Ask questions and get useful answers", "02 / 06"),
    "talk": (
        "Talk to a Personality",
        "Explore ideas through AI role-play",
        "03 / 06",
    ),
    "quiz": ("Quiz", "Test your knowledge and track your score", "04 / 06"),
    "translate": (
        "Translator",
        "Translate text between multiple languages",
        "05 / 06",
    ),
    "resume": (
        "Resume Assistant",
        "Build a clear professional resume",
        "06 / 06",
    ),
}


def _font(size):
    return ImageFont.load_default(size=size)


@lru_cache(maxsize=len(BANNERS))
def _banner_bytes(mode):
    if mode not in BANNERS:
        raise ValueError(f"Unknown banner mode: {mode}")

    title, subtitle, number = BANNERS[mode]
    image = Image.new("RGB", (WIDTH, HEIGHT), (12, 26, 43))
    draw = ImageDraw.Draw(image)

    white = (241, 245, 249)
    muted = (160, 175, 191)
    teal = (54, 211, 168)
    panel = (19, 42, 65)
    panel_accent = (23, 62, 78)
    divider = (70, 91, 110)

    # Abstract right-side composition matching the existing project artwork.
    draw.rounded_rectangle(
        (720, -65, 1175, 380),
        radius=60,
        fill=panel,
    )
    draw.rounded_rectangle(
        (820, -40, 1175, 270),
        radius=55,
        fill=panel_accent,
    )
    draw.ellipse((820, 175, 1010, 365), outline=teal, width=3)
    draw.ellipse((1020, 430, 1094, 504), fill=(27, 45, 63))
    draw.line((1043, 467, 1068, 467), fill=white, width=4)
    draw.line((1059, 458, 1068, 467), fill=white, width=4)
    draw.line((1059, 476, 1068, 467), fill=white, width=4)
    draw.line((1120, 95, 1160, 95), fill=teal, width=3)

    x = 78
    draw.text((x, 62), "TELEGRAM × AI", font=_font(18), fill=teal)

    title_font = _font(58)
    if draw.textbbox((0, 0), title, font=title_font)[2] > 600:
        title_font = _font(48)

    draw.text((x, 180), title, font=title_font, fill=white)
    draw.text((x, 270), subtitle, font=_font(26), fill=muted)
    draw.line((x, 390, 600, 390), fill=divider, width=2)
    draw.text((x, 425), number, font=_font(15), fill=muted)
    draw.text(
        (158, 425),
        "LEARNING • PRACTICE • IDEAS",
        font=_font(17),
        fill=muted,
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def english_banner_file(mode):
    """Return a fresh file-like object suitable for Telegram upload."""
    file = BytesIO(_banner_bytes(mode))
    file.name = f"{mode}_en.png"
    return file
