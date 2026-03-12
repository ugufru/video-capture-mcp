import base64
import io
import tempfile
from pathlib import Path

from mcp.types import ImageContent, TextContent
from PIL import Image

TEMP_DIR = Path(tempfile.gettempdir()) / "video-capture-mcp"


def ensure_temp_dir() -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return TEMP_DIR


def image_to_base64(image: Image.Image) -> str:
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def numpy_to_base64(frame) -> str:
    import cv2

    _, buf = cv2.imencode(".png", frame)
    return base64.standard_b64encode(buf.tobytes()).decode("utf-8")


def make_image_result(
    image_data: str,
    text: str | None = None,
    mime_type: str = "image/png",
) -> list[TextContent | ImageContent]:
    content: list[TextContent | ImageContent] = []
    if text:
        content.append(TextContent(type="text", text=text))
    content.append(
        ImageContent(type="image", data=image_data, mimeType=mime_type)
    )
    return content
