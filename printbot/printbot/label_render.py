"""Render text into a 696px tape-width image for the 62mm Brother QL tape.

Why 696? brother_ql (which qlapi uses under the hood) converts the submitted
image at 300dpi, and 62mm @ 300dpi == 696px. The tape is continuous, so its
fixed dimension is the *width*; length is whatever the label content needs.

Orientation is purely *which* dimension you render at 696px, paired with the
matching rotate flag:

- WIDTH_FIXED: image width == 696, height grows to fit. brother_ql prints it
  as-is (rotate=False). The classic "long wrapped text on a 62mm-wide strip".
- HEIGHT_FIXED: image height == 696, width grows. brother_ql rotates 90deg so
  the 696px dimension lands on the tape's width (rotate=True). Best for a
  short, wide, nameplate-style label.
"""
from dataclasses import dataclass
from enum import Enum
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

FIXED_DOTS = 696
MARGIN = 20
MIN_FONT_SIZE = 24
MAX_FONT_SIZE = 200
FONT_SIZE_STEP = 16
DEFAULT_FONT_SIZE = 64
LINE_LEADING = 6  # extra px of vertical space between baselines


class Orientation(str, Enum):
    WIDTH_FIXED = "width_fixed"  # 62mm wide, flexible length (default)
    HEIGHT_FIXED = "height_fixed"  # 62mm tall, flexible length

    @property
    def other(self) -> "Orientation":
        return (
            Orientation.HEIGHT_FIXED
            if self is Orientation.WIDTH_FIXED
            else Orientation.WIDTH_FIXED
        )

    @property
    def rotate(self) -> bool:
        """The rotate flag passed to qlapi: HEIGHT_FIXED must rotate 90deg so
        its 696px dimension lands on the tape's fixed width."""
        return self is Orientation.HEIGHT_FIXED

    @property
    def description(self) -> str:
        return (
            "62mm width, flexible length"
            if self is Orientation.WIDTH_FIXED
            else "62mm height, flexible length"
        )


@dataclass(frozen=True)
class LabelPreview:
    image: Image.Image
    font_size: int  # the size actually rendered at (< requested if shrunk)
    shrunk: bool  # True if HEIGHT_FIXED had to auto-reduce size to fit


def _line_height(font) -> int:
    _, top, _, bottom = font.getbbox("Ag")
    return bottom - top + LINE_LEADING


def _wrap_line(text: str, font, max_width: int) -> list[str]:
    """Word-wrap a single hard-break line to fit max_width, hard-breaking a
    single word that alone still exceeds the width.
    """
    words = text.split()
    if not words:
        # A user-typed blank line is a real hard break; keep it as an empty
        # row rather than silently collapsing it away.
        return [""]

    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and font.getlength(candidate) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
        # Checked for *every* word, not just after a flush: a first word that
        # alone exceeds the width would otherwise be drawn at a negative x and
        # silently clipped off both edges of the tape.
        while font.getlength(current) > max_width:
            # Grow the prefix while it still fits; cut starts at 1 so at least
            # one char is always consumed and this can't spin forever even if a
            # single glyph is wider than the tape.
            cut = 1
            while cut < len(current) and font.getlength(current[: cut + 1]) <= max_width:
                cut += 1
            lines.append(current[:cut])
            current = current[cut:]
    if current:
        lines.append(current)
    return lines


def render_label(text: str, orientation: Orientation, font_size: int) -> LabelPreview:
    font = ImageFont.load_default(size=font_size)
    line_h = _line_height(font)
    hard_lines = text.split("\n")
    inner_max = FIXED_DOTS - 2 * MARGIN

    if orientation is Orientation.WIDTH_FIXED:
        wrapped: list[str] = []
        for line in hard_lines:
            wrapped.extend(_wrap_line(line, font, inner_max))
        height = len(wrapped) * line_h + 2 * MARGIN
        image = Image.new("L", (FIXED_DOTS, height), 255)
        draw = ImageDraw.Draw(image)
        for i, line in enumerate(wrapped):
            w = draw.textlength(line, font=font)
            x = (FIXED_DOTS - w) // 2
            draw.text((x, MARGIN + i * line_h), line, font=font, fill=0)
        return LabelPreview(image=image, font_size=font_size, shrunk=False)

    # HEIGHT_FIXED: keep hard lines whole, shrink size until they fit the height.
    total = len(hard_lines) * line_h
    eff = font_size
    shrunk = False
    while total > inner_max and eff > MIN_FONT_SIZE:
        eff = max(MIN_FONT_SIZE, eff - FONT_SIZE_STEP)
        font = ImageFont.load_default(size=eff)
        line_h = _line_height(font)
        total = len(hard_lines) * line_h
        shrunk = True
    width = int(max((font.getlength(l) for l in hard_lines), default=0)) + 2 * MARGIN
    image = Image.new("L", (width, FIXED_DOTS), 255)
    draw = ImageDraw.Draw(image)
    y = (FIXED_DOTS - total) // 2
    for line in hard_lines:
        w = draw.textlength(line, font=font)
        x = (width - w) // 2
        draw.text((int(x), y), line, font=font, fill=0)
        y += line_h
    return LabelPreview(image=image, font_size=eff, shrunk=shrunk)


def to_png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
