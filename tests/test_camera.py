import pytest

from video_capture_mcp.camera import list_cameras, capture_frame, record_video


def test_list_cameras_returns_list_of_dicts():
    cameras = list_cameras()
    assert isinstance(cameras, list)
    assert len(cameras) > 0
    for cam in cameras:
        assert isinstance(cam, dict)
        assert "index" in cam
        assert "width" in cam
        assert "height" in cam
        assert "available" in cam


def _any_camera_available() -> bool:
    cameras = list_cameras()
    return any(c["available"] for c in cameras)


@pytest.mark.skipif(not _any_camera_available(), reason="No camera available")
def test_capture_frame():
    frame = capture_frame(device_index=0)
    assert frame is not None
    assert frame.shape[0] > 0
    assert frame.shape[1] > 0


@pytest.mark.skipif(not _any_camera_available(), reason="No camera available")
def test_record_video():
    file_path, frames = record_video(device_index=0, duration_seconds=1.0, fps=5.0)
    assert isinstance(file_path, str)
    assert file_path.endswith(".mp4")
    assert isinstance(frames, list)
    assert len(frames) > 0
