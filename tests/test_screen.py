from unittest.mock import patch

import pytest
from PIL import Image

from video_capture_mcp.screen import capture_screen, list_screens, list_windows


def _screen_capture_available() -> bool:
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        return img is not None and img.size[0] > 0
    except Exception:
        return False


# --- Mock-based tests (run everywhere) ---


def _make_fake_screen(width=800, height=600):
    """Create a non-uniform fake image that won't trigger blank detection."""
    img = Image.new("RGB", (width, height), color=(100, 150, 200))
    # Add a different pixel so it's not solid
    img.putpixel((0, 0), (255, 0, 0))
    return img


def test_capture_screen_default_with_mock():
    fake = _make_fake_screen()
    with patch("video_capture_mcp.screen.ImageGrab") as mock_grab:
        mock_grab.grab.return_value = fake
        result = capture_screen()
        assert result.size == (800, 600)
        mock_grab.grab.assert_called_once()


def test_capture_screen_region_with_mock():
    fake = _make_fake_screen(400, 300)
    with patch("video_capture_mcp.screen.ImageGrab") as mock_grab:
        mock_grab.grab.return_value = fake
        result = capture_screen(region=(0, 0, 400, 300))
        mock_grab.grab.assert_called_once_with(bbox=(0, 0, 400, 300))
        assert result.size == (400, 300)


def test_capture_screen_window_name_not_found():
    with patch("video_capture_mcp.screen.list_windows", return_value=[]):
        with pytest.raises(RuntimeError, match="No window found"):
            capture_screen(window_name="NonExistentApp12345")


def test_capture_screen_blank_detection():
    blank = Image.new("RGB", (800, 600), color=(0, 0, 0))
    with patch("video_capture_mcp.screen.ImageGrab") as mock_grab:
        mock_grab.grab.return_value = blank
        with pytest.raises(RuntimeError, match="screen recording permission"):
            capture_screen()


# --- Hardware-gated tests (need screen recording permission) ---


@pytest.mark.skipif(not _screen_capture_available(), reason="Screen capture not available")
def test_list_screens():
    screens = list_screens()
    assert isinstance(screens, list)
    assert len(screens) > 0
    for s in screens:
        assert "index" in s
        assert "width" in s
        assert "height" in s
        assert "is_main" in s


@pytest.mark.skipif(not _screen_capture_available(), reason="Screen capture not available")
def test_list_windows():
    windows = list_windows()
    assert isinstance(windows, list)
    for w in windows:
        assert "window_id" in w
        assert "owner" in w
        assert "name" in w
        assert "bounds" in w


@pytest.mark.skipif(not _screen_capture_available(), reason="Screen capture not available")
def test_capture_screen_default():
    image = capture_screen()
    assert isinstance(image, Image.Image)
    assert image.size[0] > 0
    assert image.size[1] > 0


@pytest.mark.skipif(not _screen_capture_available(), reason="Screen capture not available")
def test_capture_screen_with_region():
    image = capture_screen(region=(0, 0, 200, 100))
    assert isinstance(image, Image.Image)
    assert image.size == (200, 100)
