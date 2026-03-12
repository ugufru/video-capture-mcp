import pytest
from PIL import Image, ImageDraw

from video_capture_mcp.imaging import compare_images, manipulate_image


def _white_image(size=(200, 200)) -> Image.Image:
    return Image.new("RGB", size, color="white")


def _image_with_rect(size=(200, 200)) -> Image.Image:
    img = Image.new("RGB", size, color="white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([50, 50, 150, 150], fill="black")
    return img


class TestCompareImages:
    def test_identical_images_ssim_is_one(self):
        img = _white_image()
        result = compare_images(img, img.copy())
        assert result["ssim"] == pytest.approx(1.0)
        assert result["change_percentage"] == pytest.approx(0.0, abs=0.1)

    def test_different_images_ssim_less_than_one(self):
        img1 = _white_image()
        img2 = _image_with_rect()
        result = compare_images(img1, img2)
        assert result["ssim"] < 1.0
        assert result["change_percentage"] > 0
        assert len(result["bounding_boxes"]) > 0

    def test_compare_returns_expected_keys(self):
        img = _white_image()
        result = compare_images(img, img.copy())
        assert "ssim" in result
        assert "change_percentage" in result
        assert "bounding_boxes" in result
        assert "diff_image" in result

    def test_compare_no_highlight(self):
        img = _white_image()
        result = compare_images(img, img.copy(), highlight_diff=False)
        assert result["diff_image"] is None


class TestManipulateImage:
    def test_crop(self):
        img = _white_image(size=(200, 200))
        result = manipulate_image(img, [{"type": "crop", "x": 10, "y": 10, "width": 50, "height": 50}])
        assert result.size == (50, 50)

    def test_resize(self):
        img = _white_image(size=(200, 200))
        result = manipulate_image(img, [{"type": "resize", "width": 100, "height": 80}])
        assert result.size == (100, 80)

    def test_rotate(self):
        img = _white_image(size=(200, 100))
        result = manipulate_image(img, [{"type": "rotate", "angle": 90}])
        assert result.size[0] > 0
        assert result.size[1] > 0

    def test_brightness(self):
        img = _white_image()
        result = manipulate_image(img, [{"type": "brightness", "factor": 1.5}])
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    def test_contrast(self):
        img = _image_with_rect()
        result = manipulate_image(img, [{"type": "contrast", "factor": 2.0}])
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    def test_annotate(self):
        img = _white_image()
        result = manipulate_image(img, [{"type": "annotate", "x": 10, "y": 10, "width": 50, "height": 50}])
        assert isinstance(result, Image.Image)
        assert result.size == img.size

    def test_unknown_operation_raises(self):
        img = _white_image()
        with pytest.raises(ValueError, match="Unknown operation type"):
            manipulate_image(img, [{"type": "nonexistent_op"}])

    def test_multiple_operations(self):
        img = _white_image(size=(200, 200))
        result = manipulate_image(img, [
            {"type": "resize", "width": 100, "height": 100},
            {"type": "brightness", "factor": 1.2},
        ])
        assert result.size == (100, 100)
