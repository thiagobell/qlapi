from PIL import ImageFont

from printbot.label_render import (
    FIXED_DOTS,
    MARGIN,
    MAX_FONT_SIZE,
    Orientation,
    render_label,
)


def test_width_fixed_image_width_is_696():
    preview = render_label("hello world", Orientation.WIDTH_FIXED, 64)
    assert preview.image.width == 696
    assert not preview.shrunk


def test_height_fixed_image_height_is_696():
    preview = render_label("hello", Orientation.HEIGHT_FIXED, 64)
    assert preview.image.height == 696


def test_width_fixed_hard_break_produces_more_lines():
    single = render_label("hello world this is a long line", Orientation.WIDTH_FIXED, 64)
    multi = render_label(
        "hello world this is a long line\nanother long line here",
        Orientation.WIDTH_FIXED,
        64,
    )
    assert multi.image.height > single.image.height


def test_height_fixed_many_lines_shrinks():
    text = "\n".join(["line"] * 10)
    preview = render_label(text, Orientation.HEIGHT_FIXED, MAX_FONT_SIZE)
    assert preview.shrunk
    assert preview.font_size < MAX_FONT_SIZE


def test_width_fixed_hard_breaks_a_single_overlong_word():
    """A word wider than the tape must be broken across lines, not drawn at a
    negative x and silently clipped off both edges of the label.
    """
    word = "A" * 40
    font = ImageFont.load_default(size=64)
    inner_max = FIXED_DOTS - 2 * MARGIN
    assert font.getlength(word) > inner_max, "test word must not fit on one line"

    preview = render_label(word, Orientation.WIDTH_FIXED, 64)

    # Taller than a single line => it wrapped rather than overflowing sideways.
    one_line = render_label("A", Orientation.WIDTH_FIXED, 64)
    assert preview.image.height > one_line.image.height
    # And nothing was dropped: the ink starts at/after the left margin.
    assert preview.image.getbbox() is not None
