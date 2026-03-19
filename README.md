# Video Capture MCP Server

A native macOS MCP server that gives Claude the ability to capture photos and video from attached cameras. Built with AVFoundation and C++ for zero-dependency, high-performance camera access.

## Features

| Tool | Description |
|------|-------------|
| **`list_devices`** | Discover available cameras with resolution and availability info |
| **`capture_photo`** | Capture a single photo, returned as a base64 PNG that Claude can see directly |
| **`capture_video`** | Record up to 30 seconds of H.264 video, optionally returning keyframe images |

## Prerequisites

- **macOS 13+** (Ventura or later)
- **Xcode Command Line Tools** — `xcode-select --install`
- **CMake** — `brew install cmake`

## Build

```bash
make build
```

This runs CMake and compiles the native binary to `cpp/build/video-capture-mcp`.

Other targets: `make clean`, `make rebuild`.

## Configuration

### Claude Code

The repo includes `.mcp.json` — just clone and build:

```json
{
  "mcpServers": {
    "video-capture": {
      "command": "./cpp/build/video-capture-mcp"
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
      "command": "/path/to/video-capture-mcp/cpp/build/video-capture-mcp"
    }
  }
}
```

## Usage Examples

### Discover cameras

> "What cameras are available on this machine?"

Claude calls `list_devices` and returns a list of cameras with their resolutions.

### Capture a photo

> "Take a photo with the built-in camera"

Claude calls `capture_photo` with `device_index=0` and receives a PNG image it can see and describe.

### Record and review video

> "Record 10 seconds of video and show me what happened"

Claude calls `capture_video` with `duration_seconds=10` and `return_frames=true`, receiving up to 5 evenly-spaced keyframes to analyze.

## Supported Cameras

The server discovers cameras via AVFoundation's `AVCaptureDeviceDiscoverySession`, finding both built-in and external devices:

- **Built-in Mac cameras** — MacBook Pro/Air, iMac, Studio Display
- **USB cameras** — any UVC-compatible webcam
- **iPhone via Continuity Camera** — appears as an external device when:
  - iPhone and Mac are on the same Wi-Fi / nearby via Bluetooth
  - iPhone screen is locked (off)
  - Both signed into the same Apple ID
  - Continuity Camera enabled in iPhone Settings > General > AirPlay & Handoff

Note: Continuity Camera exposes only the iPhone's main wide camera as a single device — the ultra-wide and telephoto lenses are not available as separate devices.

## Architecture

- **AVFoundation** — native macOS camera access, no OpenCV dependency
- **nlohmann/json** — JSON-RPC protocol handling (fetched by CMake)
- **MCP stdio transport** — reads JSON-RPC from stdin, writes to stdout
- **H.264 via AVAssetWriter** — hardware-accelerated video encoding

## Design Decisions

- **5 warm-up frames** — USB cameras auto-expose over the first few frames. Discarding them ensures accurate capture.
- **Video capped at 30 seconds** — MCP tools should return promptly.
- **Native binary** — eliminates Python/OpenCV startup overhead (~2s → instant).

## License

MIT
