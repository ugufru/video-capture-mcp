#pragma once
#include <cstdint>
#include <string>
#include <vector>

struct CameraInfo {
    int index;
    std::string name;
    std::string unique_id;
    int width;
    int height;
    bool available;
};

struct CaptureResult {
    std::vector<uint8_t> png_data;
    int width;
    int height;
    std::string camera_name;
};

struct VideoResult {
    std::string file_path;
    std::vector<std::vector<uint8_t>> keyframe_pngs;
    int frame_count;
    std::string camera_name;
};

// List all available cameras via AVFoundation
std::vector<CameraInfo> list_cameras();

// Capture a single frame as PNG
CaptureResult capture_photo(int device_index, int width = 0, int height = 0);

// Record video to MP4, optionally extract keyframes
VideoResult record_video(int device_index, double duration_seconds = 5.0,
                         double fps = 15.0, bool return_frames = false);
