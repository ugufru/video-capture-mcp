# Video Capture MCP Server

A cross-platform MCP server that gives Claude the ability to capture photos and video from attached cameras. Works on macOS, Linux, and Raspberry Pi.

## Features

| Tool | Description |
|------|-------------|
| **`list_devices`** | Discover available cameras — probes indices 0-9 and returns resolution and availability |
| **`capture_photo`** | Capture a single photo from any camera, returned as a base64 PNG that Claude can see directly |
| **`capture_video`** | Record up to 30 seconds of video, returning either an MP4 file path or up to 5 sampled keyframes as images |

## Tech Stack

- **Python 3.10+** with **uv** for project/dependency management
- **MCP SDK** (FastMCP) for Claude integration
- **OpenCV** (`opencv-python-headless`) for camera capture and video recording
- **Pillow** for image encoding

## Prerequisites

- **Python 3.10+**
- **uv** — install via `curl -LsSf https://astral.sh/uv/install.sh | sh`

### Raspberry Pi / Linux

Install OpenCV system dependencies:

```bash
sudo apt install -y libgl1 libglib2.0-0 libsm6 libxext6 libxrender1
```

If using a USB camera, ensure it shows up via `v4l2-ctl --list-devices` or `ls /dev/video*`.

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

## Design Decisions

- **opencv-python-headless** — No GUI dependencies, works on headless servers and Raspberry Pi.
- **Codec fallback** — Tries `mp4v` first, falls back to `MJPG` for environments with limited codec support.
- **5 warm-up frames** — USB cameras on macOS auto-expose over the first few frames. Discarding them ensures accurate capture.
- **Video capped at 30 seconds** — MCP tools should return promptly.

## License

MIT
