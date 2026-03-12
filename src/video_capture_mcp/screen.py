import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageGrab

from .utils import ensure_temp_dir


def list_screens() -> list[dict]:
    """Enumerate displays using macOS CoreGraphics via Swift."""
    script = """
import Cocoa
import Foundation

let maxDisplays: UInt32 = 16
var displays = [CGDirectDisplayID](repeating: 0, count: Int(maxDisplays))
var displayCount: UInt32 = 0
CGGetActiveDisplayList(maxDisplays, &displays, &displayCount)

var result: [[String: Any]] = []
for i in 0..<Int(displayCount) {
    let d = displays[i]
    let bounds = CGDisplayBounds(d)
    result.append([
        "index": i,
        "width": Int(bounds.width),
        "height": Int(bounds.height),
        "is_main": CGDisplayIsMain(d) != 0
    ])
}

if let data = try? JSONSerialization.data(withJSONObject: result),
   let str = String(data: data, encoding: .utf8) {
    print(str)
}
"""
    try:
        proc = subprocess.run(
            ["swift", "-e", script],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to list screens: {proc.stderr.strip()}")
        return json.loads(proc.stdout.strip())
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timed out enumerating displays")
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse display list")


def list_windows() -> list[dict]:
    """List visible windows using macOS CoreGraphics via Swift."""
    script = """
import Cocoa
import Foundation

let options = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
guard let windowList = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
    print("[]")
    exit(0)
}

var result: [[String: Any]] = []
for win in windowList {
    guard let windowId = win[kCGWindowNumber as String] as? Int,
          let owner = win[kCGWindowOwnerName as String] as? String,
          let bounds = win[kCGWindowBounds as String] as? [String: Any],
          let w = bounds["Width"] as? Double,
          let h = bounds["Height"] as? Double,
          w > 0, h > 0 else { continue }

    let name = win[kCGWindowName as String] as? String ?? ""
    let x = bounds["X"] as? Double ?? 0
    let y = bounds["Y"] as? Double ?? 0

    result.append([
        "window_id": windowId,
        "owner": owner,
        "name": name,
        "bounds": ["x": Int(x), "y": Int(y), "width": Int(w), "height": Int(h)]
    ])
}

if let data = try? JSONSerialization.data(withJSONObject: result),
   let str = String(data: data, encoding: .utf8) {
    print(str)
}
"""
    try:
        proc = subprocess.run(
            ["swift", "-e", script],
            capture_output=True, text=True, timeout=10,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to list windows: {proc.stderr.strip()}")
        return json.loads(proc.stdout.strip())
    except subprocess.TimeoutExpired:
        raise RuntimeError("Timed out listing windows")
    except json.JSONDecodeError:
        raise RuntimeError("Failed to parse window list")


def _check_blank(image: Image.Image) -> None:
    """Detect blank screenshots that indicate missing screen recording permission."""
    extrema = image.convert("RGB").getextrema()
    # If all channels have zero range, the image is a solid color (likely blank)
    if all(lo == hi for lo, hi in extrema):
        raise RuntimeError(
            "Screenshot appears blank — screen recording permission may be required. "
            "Go to System Settings > Privacy & Security > Screen Recording and enable "
            "access for this application."
        )


def capture_screen(
    display_index: int | None = None,
    window_id: int | None = None,
    window_name: str | None = None,
    region: tuple[int, int, int, int] | None = None,
) -> Image.Image:
    """Capture a screenshot. Returns a PIL Image.

    Args:
        display_index: Capture a specific display (0-based).
        window_id: Capture a specific window by its CGWindowID.
        window_name: Capture a window matching this name (substring, case-insensitive).
        region: Crop region as (x, y, width, height).
    """
    temp_dir = ensure_temp_dir()
    tmp_path = str(temp_dir / "screenshot.png")

    try:
        if window_name is not None:
            # Resolve window_name to window_id
            windows = list_windows()
            match = None
            search = window_name.lower()
            for w in windows:
                if search in w["owner"].lower() or search in w["name"].lower():
                    match = w
                    break
            if match is None:
                raise RuntimeError(
                    f"No window found matching '{window_name}'. "
                    f"Available windows: {[w['owner'] + ': ' + w['name'] for w in windows[:10]]}"
                )
            window_id = match["window_id"]

        if window_id is not None:
            # Capture specific window (no shadow)
            proc = subprocess.run(
                ["screencapture", "-l", str(window_id), "-o", "-x", tmp_path],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"screencapture failed: {proc.stderr.strip()}")
            image = Image.open(tmp_path)

        elif display_index is not None:
            # Capture specific display (screencapture uses 1-based index)
            proc = subprocess.run(
                ["screencapture", "-D", str(display_index + 1), "-x", tmp_path],
                capture_output=True, text=True, timeout=10,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"screencapture failed: {proc.stderr.strip()}")
            image = Image.open(tmp_path)

        elif region is not None:
            # Region-only capture via ImageGrab
            x, y, w, h = region
            image = ImageGrab.grab(bbox=(x, y, x + w, y + h))

        else:
            # Default: main display
            image = ImageGrab.grab()

        # Apply region crop if combined with window/display capture
        if region is not None and (window_id is not None or display_index is not None):
            x, y, w, h = region
            image = image.crop((x, y, x + w, y + h))

        _check_blank(image)
        return image

    finally:
        # Clean up temp file
        tmp = Path(tmp_path)
        if tmp.exists():
            tmp.unlink()
