# Video Capture MCP Server

An MCP (Model Context Protocol) server that gives Claude the ability to capture photos and video from attached cameras, perform OCR on screens, and compare/manipulate images. This lets Claude "see" the physical world — debug by looking at an LCD screen, monitor a 3D print, read serial output, or detect visual changes over time.

## Features

### MCP Tools

| Tool | Description |
|------|-------------|
| **`list_devices`** | Discover available cameras — probes indices 0–9 and returns resolution and availability for each |
| **`capture_photo`** | Capture a single photo from any camera, returned as a base64 PNG that Claude can see directly |
| **`capture_video`** | Record up to 30 seconds of video, returning either an MP4 file path or up to 5 sampled keyframes as images |
| **`ocr_image`** | Extract text from a photo or live capture using Tesseract OCR with automatic preprocessing for LCD/OLED screens |
| **`compare_images`** | Compare two images using SSIM, returning a similarity score, change percentage, bounding boxes, and a highlighted diff image |
| **`manipulate_image`** | Apply sequential image operations — crop, resize, rotate, annotate, brightness, and contrast adjustments |

## Tech Stack

- **Python 3.10+** with **uv** for project/dependency management
- **MCP SDK** (FastMCP) for Claude integration
- **OpenCV** (`opencv-python`) for camera capture and video recording
- **Pillow** for image manipulation
- **pytesseract** for OCR (lightweight alternative to easyocr — no PyTorch dependency)
- **scikit-image** for image comparison (SSIM)

## Prerequisites

- **Python 3.10+**
- **uv** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Tesseract** — required for the `ocr_image` tool:
  ```bash
  brew install tesseract
  ```

## Project Structure

```
video-capture-mcp/
├── pyproject.toml
├── README.md
├── .mcp.json
├── issues.jsonl
├── src/
│   └── video_capture_mcp/
│       ├── __init__.py
│       ├── server.py        # FastMCP instance + all tool definitions
│       ├── camera.py        # OpenCV: list devices, capture photo, record video
│       ├── ocr.py           # pytesseract wrapper with preprocessing
│       ├── imaging.py       # Image comparison (SSIM) + manipulation (Pillow)
│       └── utils.py         # Base64 encoding, temp file mgmt, result helpers
└── tests/
    ├── test_camera.py
    ├── test_ocr.py
    └── test_imaging.py
```

## Installation

```bash
cd video-capture-mcp
uv sync
```

## Configuration

### Claude Code

Add to your `.mcp.json` (project root or `~/.claude/.mcp.json`):

```json
{
  "mcpServers": {
    "video-capture": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/video-capture-mcp", "video-capture-mcp"]
    }
  }
}
```

### Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "video-capture": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/video-capture-mcp", "video-capture-mcp"]
    }
  }
}
```

## Usage Examples

### Discover cameras

> "What cameras are available on this machine?"

Claude calls `list_devices` and returns a list of camera indices with their resolutions.

### Capture a photo

> "Take a photo with the built-in camera"

Claude calls `capture_photo` with `device_index=0` and receives a PNG image it can see and describe.

### Record and review video

> "Record 10 seconds of video and show me what happened"

Claude calls `capture_video` with `duration_seconds=10` and `return_frames=True`, receiving 5 evenly-spaced keyframes to analyze.

### Read text from a screen

> "Read what's on the LCD screen connected to my Arduino"

Claude calls `ocr_image` with `image_source="capture"`, which captures a photo and runs OCR with automatic preprocessing optimized for LCD/OLED displays.

### Detect visual changes

> "Compare what the screen looks like now vs the last photo"

Claude calls `compare_images` with one saved image path and `"capture"` for the other, returning an SSIM score and a diff image highlighting what changed.

### Annotate an image

> "Add a red rectangle around the error message in that screenshot"

Claude calls `manipulate_image` with a crop or annotate operation to highlight the region of interest.

## Roadmap

- [ ] Project scaffolding and build setup
- [ ] Shared utilities module (`make_image_result`, temp dir, base64 helpers)
- [ ] Camera device listing (`list_devices` tool)
- [ ] Photo capture with warm-up frames (`capture_photo` tool)
- [ ] Video capture with keyframe extraction (`capture_video` tool)
- [ ] OCR with preprocessing pipeline (`ocr_image` tool)
- [ ] Image comparison with SSIM (`compare_images` tool)
- [ ] Image manipulation (`manipulate_image` tool)
- [ ] End-to-end tests and error handling
- [ ] Documentation and Claude Code configuration

### Future

- **Raspberry Pi support** — `opencv-python-headless` for headless environments, `picamera2` for CSI cameras, V4L2 for USB cameras, `apt install tesseract-ocr` instead of Homebrew
- **Streaming/polling mode** — watch for changes and notify Claude automatically
- **Audio capture** — record audio alongside video

## Design Decisions

- **pytesseract over easyocr** — Avoids pulling in PyTorch (~2GB). Tesseract is sufficient for reading LCD/serial text.
- **OpenCV over subprocess (ffmpeg/imagesnap)** — Single consistent API for all camera operations, no stdout parsing.
- **5 warm-up frames** — USB cameras on macOS auto-expose over the first few frames. Discarding them is critical for accurate capture.
- **Video capped at 30 seconds** — MCP tools should return promptly.
- **Return preprocessed image from OCR** — Helps debug OCR failures without extra round trips.

## License

MIT
