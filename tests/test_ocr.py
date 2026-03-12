import pytest
from PIL import Image, ImageDraw

from video_capture_mcp.ocr import preprocess_image, extract_text


def _make_test_image() -> Image.Image:
    """Create a synthetic image with 'Hello World' text on a white background."""
    img = Image.new("RGB", (400, 100), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 30), "Hello World", fill="black")
    return img


@pytest.fixture
def test_image():
    return _make_test_image()


class TestPreprocessImage:
    def test_mode_none(self, test_image):
        result = preprocess_image(test_image, mode="none")
        assert isinstance(result, Image.Image)
        assert result.mode == "L"

    def test_mode_threshold(self, test_image):
        result = preprocess_image(test_image, mode="threshold")
        assert isinstance(result, Image.Image)

    def test_mode_blur(self, test_image):
        result = preprocess_image(test_image, mode="blur")
        assert isinstance(result, Image.Image)

    def test_mode_auto(self, test_image):
        try:
            result = preprocess_image(test_image, mode="auto")
            assert isinstance(result, Image.Image)
        except (RuntimeError, Exception) as exc:
            if "tesseract" in str(exc).lower() or "TesseractNotFoundError" in type(exc).__name__:
                pytest.skip("Tesseract not installed")
            raise


class TestExtractText:
    def test_extract_text_contains_hello(self, test_image):
        try:
            text, preprocessed = extract_text(test_image, preprocess="threshold")
            assert isinstance(text, str)
            assert isinstance(preprocessed, Image.Image)
            assert "Hello" in text
        except RuntimeError:
            pytest.skip("Tesseract not installed")

    def test_extract_text_returns_tuple(self, test_image):
        try:
            result = extract_text(test_image, preprocess="none")
            assert isinstance(result, tuple)
            assert len(result) == 2
        except RuntimeError:
            pytest.skip("Tesseract not installed")
