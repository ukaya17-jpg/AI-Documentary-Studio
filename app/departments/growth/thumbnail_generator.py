"""Growth stage: generate a thumbnail from a real rendered frame + the SEO
title -- no AI image-generation API, no new cost. Reuses the already-
downloaded/rendered video and the already-generated SEO title.

Best-effort and informational only: on any failure this returns "" rather
than raising, matching the same non-blocking philosophy as quality_critic.
"""

import os

from loguru import logger
from moviepy import VideoFileClip
from PIL import Image, ImageDraw, ImageFont

from app.config import config
from app.models.seo import SeoMetadata
from app.utils import utils

_DEFAULT_FONT_NAME = "BeVietnamPro-Bold.ttf"
_MAX_TITLE_LINES = 3
_MIN_FONT_SCALE = 0.6
_FONT_SCALE_STEP = 0.05
_ELLIPSIS = "..."


def _extract_middle_frame(video_path: str, output_path: str) -> bool:
    """Extract a single frame from the middle of the video's duration.

    Autonomous decision (overnight session, logged in PROGRESS.md): picking
    the middle timestamp is the conservative choice -- scene-importance-based
    selection would need scene<->timeline timestamp mapping that the legacy
    combine_videos() timeline doesn't expose reliably (looping/trimming).
    """
    try:
        clip = VideoFileClip(video_path)
        try:
            timestamp = clip.duration / 2
            clip.save_frame(output_path, t=timestamp)
        finally:
            clip.close()
        return True
    except Exception as e:
        logger.warning(f"thumbnail_generator: failed to extract frame from {video_path!r}: {e}")
        return False


def _font_scales() -> list[float]:
    """[1.0, 0.95, 0.90, ..., down to _MIN_FONT_SCALE]."""
    scales = []
    scale = 1.0
    while scale > _MIN_FONT_SCALE:
        scales.append(round(scale, 2))
        scale -= _FONT_SCALE_STEP
    scales.append(_MIN_FONT_SCALE)
    return scales


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Greedy word-wrap. Returns however many lines the text needs -- the
    caller decides what to do if that's more than it wants to display."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = (current + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _truncate_with_ellipsis(
    draw: ImageDraw.ImageDraw, line: str, font: ImageFont.FreeTypeFont, max_width: int
) -> str:
    """Shorten `line` character by character until `line + "..."` fits."""
    if draw.textlength(line + _ELLIPSIS, font=font) <= max_width:
        return line + _ELLIPSIS
    while line and draw.textlength(line + _ELLIPSIS, font=font) > max_width:
        line = line[:-1].rstrip()
    return (line + _ELLIPSIS) if line else _ELLIPSIS


def _overlay_title(image_path: str, title: str) -> bool:
    if not title.strip():
        return True  # no title to overlay; keep the raw frame as-is

    try:
        img = Image.open(image_path).convert("RGBA")
        w, h = img.size

        # Darken the bottom band so white text stays legible over any footage.
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        band_draw = ImageDraw.Draw(overlay)
        band_top = int(h * 0.62)
        for y in range(band_top, h):
            alpha = int(190 * (y - band_top) / max(1, h - band_top))
            band_draw.line([(0, y), (w, y)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img, overlay)

        draw = ImageDraw.Draw(img)
        font_name = config.ui.get("font_name", _DEFAULT_FONT_NAME)
        font_path = os.path.join(utils.font_dir(), font_name)
        base_font_size = int(w * 0.085)

        margin = int(w * 0.06)
        max_width = w - 2 * margin

        # Shrink-and-retry: try progressively smaller font sizes until the
        # title fits within _MAX_TITLE_LINES. If it still doesn't fit at the
        # smallest scale, truncate the last line with an ellipsis instead of
        # silently dropping the overflow words.
        font_size = base_font_size
        font = ImageFont.truetype(font_path, font_size)
        lines: list[str] = []
        for scale in _font_scales():
            font_size = max(1, int(base_font_size * scale))
            font = ImageFont.truetype(font_path, font_size)
            lines = _wrap_text(draw, title, font, max_width)
            if len(lines) <= _MAX_TITLE_LINES:
                break

        if len(lines) > _MAX_TITLE_LINES:
            lines = lines[:_MAX_TITLE_LINES]
            lines[-1] = _truncate_with_ellipsis(draw, lines[-1], font, max_width)

        line_height = int(font_size * 1.15)
        total_text_h = line_height * len(lines)
        y = h - int(h * 0.08) - total_text_h
        for line in lines:
            tw = draw.textlength(line, font=font)
            x = (w - tw) / 2
            draw.text(
                (x, y), line, font=font, fill="#FFFFFF", stroke_width=6, stroke_fill="#000000"
            )
            y += line_height

        img.convert("RGB").save(image_path)
        return True
    except Exception as e:
        logger.warning(f"thumbnail_generator: failed to overlay title on {image_path!r}: {e}")
        return False


def generate_thumbnail(combined_video_path: str, seo: SeoMetadata | None, task_id: str) -> str:
    """Returns the thumbnail file path, or "" if generation failed at any step."""
    if not combined_video_path or not os.path.exists(combined_video_path):
        logger.warning(
            f"thumbnail_generator: combined video not found: {combined_video_path!r}"
        )
        return ""

    task_directory = utils.task_dir(task_id)
    output_path = os.path.join(task_directory, "thumbnail.png")

    if not _extract_middle_frame(combined_video_path, output_path):
        return ""

    title = seo.title if seo else ""
    if not _overlay_title(output_path, title):
        return ""

    return output_path
