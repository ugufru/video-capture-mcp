"""Image comparison (SSIM) and manipulation (Pillow)."""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance
from skimage.metrics import structural_similarity


def compare_images(
    image1: Image.Image,
    image2: Image.Image,
    highlight_diff: bool = True,
) -> dict:
    """Compare two images using SSIM and return difference metrics."""
    gray1 = np.array(image1.convert("L"))
    gray2 = np.array(image2.convert("L"))

    if gray1.shape != gray2.shape:
        gray2 = np.array(image2.resize(image1.size).convert("L"))

    score, diff = structural_similarity(gray1, gray2, full=True)

    diff_uint8 = (diff * 255).astype("uint8")
    thresh = cv2.threshold(
        diff_uint8, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )[1]

    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    total_pixels = thresh.shape[0] * thresh.shape[1]
    change_percentage = float(cv2.countNonZero(thresh) / total_pixels * 100)

    bounding_boxes = []
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        bounding_boxes.append({"x": x, "y": y, "w": w, "h": h})

    diff_image = None
    if highlight_diff:
        annotated = image1.convert("RGB").copy()
        draw = ImageDraw.Draw(annotated)
        for box in bounding_boxes:
            draw.rectangle(
                [box["x"], box["y"], box["x"] + box["w"], box["y"] + box["h"]],
                outline="red",
            )
        diff_image = annotated

    return {
        "ssim": float(score),
        "change_percentage": change_percentage,
        "bounding_boxes": bounding_boxes,
        "diff_image": diff_image,
    }


def manipulate_image(
    image: Image.Image, operations: list[dict]
) -> Image.Image:
    """Apply a sequence of operations to an image and return the result."""
    for op in operations:
        op_type = op.get("type")

        if op_type == "crop":
            x, y = op["x"], op["y"]
            image = image.crop((x, y, x + op["width"], y + op["height"]))

        elif op_type == "resize":
            image = image.resize((op["width"], op["height"]), Image.LANCZOS)

        elif op_type == "rotate":
            image = image.rotate(op["angle"], expand=True)

        elif op_type == "brightness":
            image = ImageEnhance.Brightness(image).enhance(op["factor"])

        elif op_type == "contrast":
            image = ImageEnhance.Contrast(image).enhance(op["factor"])

        elif op_type == "annotate":
            draw = ImageDraw.Draw(image)
            x, y = op["x"], op["y"]
            w, h = op["width"], op["height"]
            color = op.get("color", "red")
            thickness = op.get("thickness", 3)
            draw.rectangle([x, y, x + w, y + h], outline=color, width=thickness)

        else:
            raise ValueError(f"Unknown operation type: {op_type}")

    return image
