import time
from pathlib import Path

import cv2
import numpy

from .utils import ensure_temp_dir


def list_cameras() -> list[dict]:
    cameras = []
    for index in range(10):
        cap = cv2.VideoCapture(index)
        available = cap.isOpened()
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if available else 0
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if available else 0
        cap.release()
        cameras.append({
            "index": index,
            "width": width,
            "height": height,
            "available": available,
        })
    return cameras


def capture_frame(
    device_index: int = 0,
    width: int | None = None,
    height: int | None = None,
) -> numpy.ndarray:
    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera at index {device_index}")

    if width is not None:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height is not None:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Discard warm-up frames (auto-exposure settling on macOS USB cameras)
    for _ in range(5):
        cap.read()

    ret, frame = cap.read()
    cap.release()

    if not ret or frame is None:
        raise RuntimeError(f"Failed to read frame from camera {device_index}")

    return frame


def record_video(
    device_index: int = 0,
    duration_seconds: float = 5.0,
    fps: float = 15.0,
) -> tuple[str, list[numpy.ndarray]]:
    duration_seconds = min(duration_seconds, 30.0)

    cap = cv2.VideoCapture(device_index)
    if not cap.isOpened():
        raise RuntimeError(f"Cannot open camera at index {device_index}")

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    temp_dir = ensure_temp_dir()
    file_path = str(temp_dir / f"recording_{int(time.time())}.mp4")

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(file_path, fourcc, fps, (frame_width, frame_height))

    frames: list[numpy.ndarray] = []
    frame_interval = 1.0 / fps
    start_time = time.time()

    while time.time() - start_time < duration_seconds:
        frame_start = time.time()
        ret, frame = cap.read()
        if not ret or frame is None:
            break
        writer.write(frame)
        frames.append(frame)

        elapsed = time.time() - frame_start
        if elapsed < frame_interval:
            time.sleep(frame_interval - elapsed)

    cap.release()
    writer.release()

    return file_path, frames
