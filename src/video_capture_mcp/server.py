import json

from mcp.server.fastmcp import FastMCP
from PIL import Image

from .camera import capture_frame, list_cameras, record_video
from .imaging import compare_images, manipulate_image
from .ocr import extract_text
from .utils import image_to_base64, make_image_result, numpy_to_base64

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


@mcp.tool()
def ocr_image(
    image_source: str = "capture",
    device_index: int = 0,
    preprocess: str = "auto",
    lang: str = "eng",
) -> list:
    """Extract text from an image using OCR. Use image_source='capture' for live camera, or provide a file path."""
    if image_source == "capture":
        frame = capture_frame(device_index)
        import cv2
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(frame_rgb)
    else:
        image = Image.open(image_source)

    text, preprocessed = extract_text(image, preprocess=preprocess, lang=lang)

    return make_image_result(
        image_to_base64(preprocessed),
        text=f"OCR Result:\n{text}" if text else "No text detected",
    )


@mcp.tool()
def compare_images_tool(
    image1_path: str,
    image2_path: str,
    device_index: int = 0,
    highlight_diff: bool = True,
) -> list:
    """Compare two images and return similarity metrics. Use 'capture' as a path to capture a live photo."""
    def load_image(path: str) -> Image.Image:
        if path == "capture":
            frame = capture_frame(device_index)
            import cv2
            return Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        return Image.open(path)

    img1 = load_image(image1_path)
    img2 = load_image(image2_path)

    result = compare_images(img1, img2, highlight_diff=highlight_diff)

    summary = (
        f"SSIM: {result['ssim']:.4f}\n"
        f"Change: {result['change_percentage']:.1f}%\n"
        f"Changed regions: {len(result['bounding_boxes'])}"
    )

    if result["diff_image"]:
        return make_image_result(image_to_base64(result["diff_image"]), text=summary)

    from mcp.types import TextContent
    return [TextContent(type="text", text=summary)]


@mcp.tool()
def manipulate_image_tool(
    image_path: str,
    operations: list[dict],
) -> list:
    """Apply sequential image operations (crop, resize, rotate, annotate, brightness, contrast)."""
    image = Image.open(image_path)
    result = manipulate_image(image, operations)

    op_types = [op.get("type", "unknown") for op in operations]
    summary = f"Applied {len(operations)} operation(s): {', '.join(op_types)}"

    return make_image_result(image_to_base64(result), text=summary)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
