"""Vision utilities — frame extraction, image handling for visual critique."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from museloop.utils.logging import get_logger

logger = get_logger(__name__)

# Image extensions directly usable by vision APIs
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}

# Max images to send per critique (controls API cost)
MAX_VISION_IMAGES = 10

# Target size for vision input (pixels on long edge) — Claude optimal is ~1568px
VISION_MAX_DIMENSION = 1568


def get_image_paths_from_assets(assets: list[dict[str, Any]]) -> list[str]:
    """Extract sendable image paths from asset list.

    For image assets, returns the path directly.
    For video assets, extracts a representative frame.
    Returns at most MAX_VISION_IMAGES paths.
    """
    image_paths: list[str] = []

    for asset in assets:
        path = asset.get("path", "")
        if not path:
            continue
        p = Path(path)
        if not p.exists():
            continue

        if p.suffix.lower() in IMAGE_EXTENSIONS:
            image_paths.append(str(p))
        elif p.suffix.lower() in VIDEO_EXTENSIONS:
            frame = extract_video_frame(str(p))
            if frame:
                image_paths.append(frame)

        if len(image_paths) >= MAX_VISION_IMAGES:
            break

    return image_paths


def extract_video_frame(video_path: str, position: float = 0.5) -> str | None:
    """Extract a single frame from a video file using OpenCV.

    Args:
        video_path: Path to the video file.
        position: Relative position in the video (0.0 = start, 1.0 = end).

    Returns:
        Path to the extracted JPEG frame, or None on failure.
    """
    try:
        import cv2

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            cap.release()
            return None

        target_frame = int(total_frames * min(max(position, 0.0), 1.0))
        cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = cap.read()
        cap.release()

        if not ret:
            return None

        frame_path = video_path + ".frame.jpg"
        cv2.imwrite(frame_path, frame)
        logger.info("video_frame_extracted", video=video_path, frame=target_frame)
        return frame_path

    except ImportError:
        logger.warning("opencv_not_available", message="Cannot extract video frames without OpenCV")
        return None
    except Exception as e:
        logger.warning("frame_extraction_failed", video=video_path, error=str(e))
        return None


def resize_for_vision(image_path: str, max_dimension: int = VISION_MAX_DIMENSION) -> str:
    """Resize an image if it exceeds max_dimension, preserving aspect ratio.

    Returns the path to the resized image (or original if no resize needed).
    """
    try:
        from PIL import Image

        img = Image.open(image_path)
        w, h = img.size

        if max(w, h) <= max_dimension:
            return image_path

        if w > h:
            new_w = max_dimension
            new_h = int(h * (max_dimension / w))
        else:
            new_h = max_dimension
            new_w = int(w * (max_dimension / h))

        resized = img.resize((new_w, new_h), Image.LANCZOS)
        resized_path = image_path + ".resized.jpg"
        resized.save(resized_path, "JPEG", quality=85)
        return resized_path

    except ImportError:
        return image_path
    except Exception:
        return image_path
