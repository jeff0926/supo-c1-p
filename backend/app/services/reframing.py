"""Subsystem 4: MediaPipe face tracking + smoothed 9:16 crop coordinates."""
from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:
    import numpy as np

logger = logging.getLogger(__name__)


class ReframingError(RuntimeError):
    pass


@dataclass
class CropTrack:
    """Smoothed crop center x-coordinates sampled at a fixed FPS."""
    fps: float
    width: int
    height: int
    crop_width: int
    centers_x: list[float]

    def center_at(self, t_seconds: float) -> float:
        if not self.centers_x:
            return self.width / 2.0
        idx = min(int(t_seconds * self.fps), len(self.centers_x) - 1)
        return self.centers_x[idx]


def _detect_faces(frame: "np.ndarray", detector) -> list[tuple[float, float, float, float]]:
    import cv2

    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = detector.process(rgb)
    boxes: list[tuple[float, float, float, float]] = []
    if not result.detections:
        return boxes
    for det in result.detections:
        bbox = det.location_data.relative_bounding_box
        x = bbox.xmin * w
        y = bbox.ymin * h
        bw = bbox.width * w
        bh = bbox.height * h
        boxes.append((x, y, bw, bh))
    return boxes


def compute_crop_track(
    video_path: Path,
    start_time: float,
    end_time: float,
    sample_fps: int | None = None,
    smoothing_window: int | None = None,
) -> CropTrack:
    """Sample the segment at `sample_fps`, run MediaPipe face detection, return a
    rolling-average smoothed series of crop centers."""
    try:
        import cv2
        import mediapipe as mp
    except ImportError as exc:
        raise ReframingError(f"required dependency missing: {exc}") from exc

    sample_fps = sample_fps or settings.reframe_fps
    smoothing_window = smoothing_window or settings.smoothing_window

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ReframingError(f"Cannot open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    if width == 0 or height == 0:
        cap.release()
        raise ReframingError("Video has zero dimensions")

    crop_width = int(height * 9 / 16)
    crop_width = min(crop_width, width)

    step_seconds = 1.0 / sample_fps
    detector = mp.solutions.face_detection.FaceDetection(
        model_selection=1, min_detection_confidence=0.5
    )

    raw_centers: list[float] = []
    last_known = width / 2.0
    t = start_time
    try:
        while t < end_time:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok:
                raw_centers.append(last_known)
                t += step_seconds
                continue
            boxes = _detect_faces(frame, detector)
            if boxes:
                boxes.sort(key=lambda b: b[2] * b[3], reverse=True)
                bx, _, bw, _ = boxes[0]
                last_known = bx + bw / 2.0
            raw_centers.append(last_known)
            t += step_seconds
    finally:
        detector.close()
        cap.release()

    smoothed = _rolling_average(raw_centers, smoothing_window)
    smoothed = [_clamp_center(c, crop_width, width) for c in smoothed]

    return CropTrack(
        fps=float(sample_fps),
        width=width,
        height=height,
        crop_width=crop_width,
        centers_x=smoothed,
    )


def _rolling_average(values: list[float], window: int) -> list[float]:
    if window <= 1 or not values:
        return list(values)
    buf: deque[float] = deque(maxlen=window)
    out: list[float] = []
    for v in values:
        buf.append(v)
        out.append(sum(buf) / len(buf))
    return out


def _clamp_center(center: float, crop_width: int, frame_width: int) -> float:
    half = crop_width / 2.0
    return max(half, min(frame_width - half, center))


def average_crop_x(track: CropTrack) -> int:
    """Return the integer left-edge x for the average crop center across the track."""
    if not track.centers_x:
        return (track.width - track.crop_width) // 2
    avg_center = sum(track.centers_x) / len(track.centers_x)
    return max(0, int(avg_center - track.crop_width / 2))
