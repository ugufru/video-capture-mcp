"""OCR module with preprocessing optimized for LCD/OLED screens."""

import numpy as np
import cv2
import pytesseract
from PIL import Image


def preprocess_image(image: Image.Image, mode: str = "auto") -> Image.Image:
    """Preprocess an image for OCR.

    Args:
        image: Input PIL image.
        mode: Preprocessing mode — "auto", "threshold", "blur", or "none".

    Returns:
        Preprocessed PIL image (grayscale).
    """
    gray = image.convert("L")

    if mode == "none":
        return gray

    if mode == "threshold":
        arr = np.array(gray)
        thresh = cv2.adaptiveThreshold(
            arr, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            blockSize=11, C=2,
        )
        return Image.fromarray(thresh)

    if mode == "blur":
        arr = np.array(gray)
        blurred = cv2.GaussianBlur(arr, (5, 5), 0)
        thresh = cv2.adaptiveThreshold(
            blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY,
            blockSize=11, C=2,
        )
        return Image.fromarray(thresh)

    if mode == "auto":
        thresh_img = preprocess_image(image, mode="threshold")
        thresh_text = pytesseract.image_to_string(thresh_img).strip()

        if len(thresh_text) < 5:
            blur_img = preprocess_image(image, mode="blur")
            blur_text = pytesseract.image_to_string(blur_img).strip()
            if len(blur_text) > len(thresh_text):
                return blur_img

        return thresh_img

    raise ValueError(f"Unknown preprocessing mode: {mode!r}")


def extract_text(
    image: Image.Image, preprocess: str = "auto", lang: str = "eng",
) -> tuple[str, Image.Image]:
    """Extract text from an image using Tesseract OCR.

    Args:
        image: Input PIL image.
        preprocess: Preprocessing mode passed to preprocess_image.
        lang: Tesseract language code.

    Returns:
        Tuple of (extracted text, preprocessed image).
    """
    preprocessed = preprocess_image(image, mode=preprocess)

    try:
        text = pytesseract.image_to_string(preprocessed, lang=lang).strip()
    except pytesseract.TesseractNotFoundError:
        raise RuntimeError(
            "Tesseract is not installed or not found on PATH. "
            "Install it with: brew install tesseract"
        )

    return text, preprocessed
