import json

from mcp.server.fastmcp import FastMCP

from .camera import capture_frame, list_cameras, record_video
from .utils import make_image_result, numpy_to_base64

mcp = FastMCP("video-capture")


@mcp.tool()
def list_devices() -> str:
    """List available camera devices with their index, resolution, and availability."""
    cameras = list_cameras()
    available = [c for c in cameras if c["available"]]
    return json.dumps(available, indent=2)


@mcp.tool()
def capture_photo(
    device_index: int = 0,
    width: int | None = None,
    height: int | None = None,
) -> list:
    """Capture a single photo from a camera. Returns the image for Claude to see."""
    frame = capture_frame(device_index, width, height)
    return make_image_result(numpy_to_base64(frame))


@mcp.tool()
def capture_video(
    device_index: int = 0,
    duration_seconds: float = 5.0,
    fps: float = 15.0,
    return_frames: bool = False,
) -> list | str:
    """Record video from a camera. Returns an MP4 file path, or up to 5 keyframes as images if return_frames=True."""
    file_path, frames = record_video(device_index, duration_seconds, fps)

    if not return_frames:
        return f"Video saved to {file_path} ({len(frames)} frames at {fps} fps)"

    # Extract up to 5 evenly-spaced keyframes
    n = min(5, len(frames))
    if n == 0:
        return "No frames captured"
    indices = [int(i * (len(frames) - 1) / (n - 1)) for i in range(n)] if n > 1 else [0]
    keyframes = [frames[i] for i in indices]

    content = []
    for i, frame in enumerate(keyframes):
        content.extend(
            make_image_result(
                numpy_to_base64(frame),
                text=f"Frame {i + 1}/{n} (from {file_path})",
            )
        )
    return content


def main():
    mcp.run()


if __name__ == "__main__":
    main()
