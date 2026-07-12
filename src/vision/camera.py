"""
Nexus Camera / Vision Service.

Captures webcam frames in real-time using OpenCV.
Runs in a background thread to avoid blocking the async event loop.
Exposes frame callbacks and a queue API for downstream processing.
"""

from __future__ import annotations

import logging
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class CameraCaptureConfig:
    """Configuration for CameraCapture."""

    device_index: int = 0
    """OpenCV camera device index."""

    width: int = 640
    """Frame width in pixels."""

    height: int = 480
    """Frame height in pixels."""

    fps: int = 15
    """Target frames per second."""


class CameraCapture:
    """Real-time webcam frame capture.

    Usage:
        camera = CameraCapture()
        camera.on_frame = lambda frame: print(f"Got frame {frame.shape}")

        async with camera:
            await camera.start()
            await asyncio.sleep(5)
            await camera.stop()
    """

    def __init__(
        self,
        config: CameraCaptureConfig | None = None,
    ) -> None:
        self.config = config or CameraCaptureConfig()

        # Callback (set before start())
        self.on_frame: Callable[[np.ndarray], None] | None = None

        # Internal state
        self._cap: Any = None
        self._thread: threading.Thread | None = None
        self._running = threading.Event()
        self._frame_queue: queue.Queue[np.ndarray | None] | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start camera capture in a background thread.

        Logs a warning and returns silently if the camera is unavailable.
        """
        if self._running.is_set():
            return

        try:
            import cv2  # noqa: F401
        except ImportError:
            logging.getLogger(__name__).error(
                "OpenCV (cv2) is not installed. Cannot start camera capture."
            )
            return

        cap = cv2.VideoCapture(self.config.device_index)
        if not cap.isOpened():
            logging.getLogger(__name__).warning(
                "Camera device %s is unavailable. Camera capture disabled.",
                self.config.device_index,
            )
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.height)
        cap.set(cv2.CAP_PROP_FPS, self.config.fps)

        self._cap = cap
        self._frame_queue = queue.Queue(maxsize=10)

        self._running.set()
        self._thread = threading.Thread(
            target=self._capture_loop,
            name="nexus-camera-capture",
            daemon=True,
        )
        self._thread.start()

    async def stop(self) -> None:
        """Stop camera capture and release resources."""
        self._running.clear()

        if self._thread and self._thread.is_alive():
            try:
                self._frame_queue.put_nowait(None)
            except Exception:
                pass
            self._thread.join(timeout=2.0)

        if self._cap is not None:
            try:
                self._cap.release()
            except Exception:
                pass
            self._cap = None

    @property
    def is_active(self) -> bool:
        """Whether camera capture is currently running."""
        return self._running.is_set() and self._cap is not None

    def get_frame(self, timeout: float = 1.0) -> np.ndarray | None:
        """Return the latest frame from the queue, or None if none available.

        Args:
            timeout: Maximum seconds to wait for a frame.
        """
        if self._frame_queue is None:
            return None
        try:
            frame = self._frame_queue.get(timeout=timeout)
            if frame is None:
                return None
            return frame
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "CameraCapture":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _capture_loop(self) -> None:
        """Background thread: captures frames from the camera."""
        logger = logging.getLogger(__name__)
        cap = self._cap
        fq = self._frame_queue

        while self._running.is_set():
            ret, frame = cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera.")
                continue

            if self.on_frame is not None:
                try:
                    self.on_frame(frame)
                except Exception:
                    pass

            try:
                fq.put_nowait(frame)
            except Exception:
                # Queue full — drop oldest
                try:
                    fq.get_nowait()
                except Exception:
                    pass
                fq.put_nowait(frame)

