"""Tests for the camera/vision module."""

from __future__ import annotations

import queue
import threading
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from src.vision.camera import CameraCapture, CameraCaptureConfig


# ------------------------------------------------------------------
# CameraCaptureConfig Tests
# ------------------------------------------------------------------

class TestCameraCaptureConfig:
    def test_default_config(self) -> None:
        config = CameraCaptureConfig()
        assert config.device_index == 0
        assert config.width == 640
        assert config.height == 480
        assert config.fps == 15

    def test_custom_config(self) -> None:
        config = CameraCaptureConfig(
            device_index=2,
            width=1280,
            height=720,
            fps=30,
        )
        assert config.device_index == 2
        assert config.width == 1280
        assert config.height == 720
        assert config.fps == 30


# ------------------------------------------------------------------
# CameraCapture Tests
# ------------------------------------------------------------------

class TestCameraCapture:
    """Tests for CameraCapture with mocked OpenCV."""

    @pytest.mark.asyncio
    async def test_importable(self) -> None:
        """Module can be imported and instantiated without errors."""
        camera = CameraCapture()
        assert not camera.is_active

    @pytest.mark.asyncio
    async def test_config_defaults(self) -> None:
        camera = CameraCapture()
        assert camera.config.device_index == 0
        assert camera.config.width == 640
        assert camera.config.height == 480
        assert camera.config.fps == 15

    @pytest.mark.asyncio
    async def test_start_with_opencv_unavailable(self) -> None:
        """Should log error and return silently if OpenCV is missing."""
        import logging

        camera = CameraCapture()
        with patch.dict("sys.modules", {"cv2": None}):
            with patch("builtins.__import__", side_effect=ImportError("No cv2")):
                logger = logging.getLogger("src.vision.camera")
                with patch.object(logger, "error") as mock_error:
                    await camera.start()
                    assert not camera.is_active
                    assert mock_error.called

    @pytest.mark.asyncio
    async def test_start_with_unavailable_camera(self) -> None:
        """Should log warning and return silently if camera is unavailable."""
        import logging

        camera = CameraCapture()
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = False

        mock_cv2 = MagicMock()
        mock_cv2.VideoCapture.return_value = mock_cap

        with patch.dict("sys.modules", {"cv2": mock_cv2}):
            logger = logging.getLogger("src.vision.camera")
            with patch.object(logger, "warning") as mock_warning:
                await camera.start()
                assert not camera.is_active
                assert mock_warning.called

    @pytest.mark.asyncio
    async def test_start_then_stop_cleanly(self) -> None:
        """Frame capture can start/stop cleanly and release resources."""
        import logging

        camera = CameraCapture()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, frame)
        mock_cap.get.side_effect = [640.0, 480.0, 15.0]

        mock_cv2 = MagicMock()
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5

        with patch.dict("sys.modules", {"cv2": mock_cv2}):
            with patch.object(logging.getLogger("src.vision.camera"), "warning"):
                await camera.start()
                assert camera.is_active

                # Wait a tick for the thread to capture at least one frame
                import time

                time.sleep(0.1)

                assert camera._thread is not None
                assert camera._thread.is_alive()

            await camera.stop()
            assert not camera.is_active
            mock_cap.release.assert_called_once()

    @pytest.mark.asyncio
    async def test_frame_callback(self) -> None:
        """Frame callback receives numpy arrays."""
        camera = CameraCapture()
        frames_received: list[np.ndarray] = []
        camera.on_frame = lambda f: frames_received.append(f)

        frame = np.zeros((240, 320, 3), dtype=np.uint8)
        mock_cap = MagicMock()
        mock_cap.isOpened.return_value = True
        mock_cap.read.return_value = (True, frame)
        mock_cap.get.side_effect = [320.0, 240.0, 15.0]

        mock_cv2 = MagicMock()
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cv2.CAP_PROP_FRAME_WIDTH = 3
        mock_cv2.CAP_PROP_FRAME_HEIGHT = 4
        mock_cv2.CAP_PROP_FPS = 5

        with patch.dict("sys.modules", {"cv2": mock_cv2}):
            with patch("logging.getLogger"):
                await camera.start()
                import time

                time.sleep(0.15)
                await camera.stop()

        assert len(frames_received) > 0
        assert frames_received[0].shape == (240, 320, 3)

    @pytest.mark.asyncio
    async def test_get_frame_from_queue(self) -> None:
        """get_frame() returns frames from the internal queue."""
        camera = CameraCapture()

        frame = np.ones((10, 10, 3), dtype=np.uint8)
        q: queue.Queue = queue.Queue()
        camera._frame_queue = q

        result = camera.get_frame()
        assert result is None

        q.put(frame)
        result = camera.get_frame()
        assert result is not None
        assert result.shape == (10, 10, 3)

    @pytest.mark.asyncio
    async def test_context_manager(self) -> None:
        """Async context manager should enter and exit cleanly."""
        camera = CameraCapture()
        async with camera:
            assert camera is not None

    def test_config_custom_resolution(self) -> None:
        config = CameraCaptureConfig(width=1920, height=1080)
        assert config.width == 1920
        assert config.height == 1080
