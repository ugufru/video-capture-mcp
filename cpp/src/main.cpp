#include "base64.h"
#include "camera.h"
#include "mcp_server.h"

#include <nlohmann/json.hpp>

using json = nlohmann::json;

int main() {
    McpServer server("video-capture", "3.0.0");

    // ── list_devices ─────────────────────────────────────────────────
    server.add_tool(
        "list_devices",
        "List available camera devices with their index, resolution, and "
        "availability.",
        {{"type", "object"}, {"properties", json::object()}},
        [](const json& /*args*/) -> json {
            auto cameras = list_cameras();
            json content = json::array();
            json device_list = json::array();
            for (auto& cam : cameras) {
                device_list.push_back(
                    {{"index", cam.index},
                     {"name", cam.name},
                     {"width", cam.width},
                     {"height", cam.height},
                     {"available", cam.available}});
            }
            content.push_back(
                {{"type", "text"},
                 {"text", device_list.dump(2)}});
            return content;
        });

    // ── capture_photo ────────────────────────────────────────────────
    json photo_schema = {
        {"type", "object"},
        {"properties",
         {{"device_index",
           {{"type", "integer"},
            {"default", 0},
            {"description", "Camera device index"}}},
          {"width",
           {{"type", "integer"},
            {"description", "Desired width (optional)"}}},
          {"height",
           {{"type", "integer"},
            {"description", "Desired height (optional)"}}}}}};

    server.add_tool(
        "capture_photo",
        "Capture a single photo from a camera. Returns the image for "
        "Claude to see.",
        photo_schema,
        [](const json& args) -> json {
            int idx = args.value("device_index", 0);
            int w = args.value("width", 0);
            int h = args.value("height", 0);

            auto result = capture_photo(idx, w, h);
            std::string b64 = base64_encode(result.png_data);

            json content = json::array();
            content.push_back(
                {{"type", "text"},
                 {"text", "Photo from " + result.camera_name}});
            content.push_back(
                {{"type", "image"},
                 {"data", b64},
                 {"mimeType", "image/png"}});
            return content;
        });

    // ── capture_video ────────────────────────────────────────────────
    json video_schema = {
        {"type", "object"},
        {"properties",
         {{"device_index",
           {{"type", "integer"},
            {"default", 0},
            {"description", "Camera device index"}}},
          {"duration_seconds",
           {{"type", "number"},
            {"default", 5},
            {"description", "Recording duration (max 30s)"}}},
          {"fps",
           {{"type", "number"},
            {"default", 15},
            {"description", "Frames per second"}}},
          {"return_frames",
           {{"type", "boolean"},
            {"default", false},
            {"description",
             "If true, return up to 5 keyframes as images"}}}}}};

    server.add_tool(
        "capture_video",
        "Record video from a camera. Returns an MP4 file path, or up to "
        "5 keyframes as images if return_frames=True.",
        video_schema,
        [](const json& args) -> json {
            int idx = args.value("device_index", 0);
            double dur = args.value("duration_seconds", 5.0);
            double fps_val = args.value("fps", 15.0);
            bool frames = args.value("return_frames", false);

            auto result = record_video(idx, dur, fps_val, frames);

            json content = json::array();

            if (frames && !result.keyframe_pngs.empty()) {
                content.push_back(
                    {{"type", "text"},
                     {"text", "Video from " + result.camera_name +
                              " (" + std::to_string(result.frame_count) +
                              " frames). Keyframes:"}});
                for (auto& png : result.keyframe_pngs) {
                    content.push_back(
                        {{"type", "image"},
                         {"data", base64_encode(png)},
                         {"mimeType", "image/png"}});
                }
            } else {
                content.push_back(
                    {{"type", "text"},
                     {"text", result.file_path}});
            }
            return content;
        });

    server.run();
    return 0;
}
