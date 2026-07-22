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
        font_size = int(w * 0.085)
        font = ImageFont.truetype(font_path, font_size)

        margin = int(w * 0.06)
        max_width = w - 2 * margin
        lines: list[str] = []
        current = ""
        for word in title.split():
            trial = (current + " " + word).strip()
            if draw.textlength(trial, font=font) <= max_width:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        lines = lines[:_MAX_TITLE_LINES]

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
