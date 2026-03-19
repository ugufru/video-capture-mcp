cmake_minimum_required(VERSION 3.20)
project(video-capture-mcp LANGUAGES CXX OBJCXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_OBJCXX_STANDARD 20)

# Fetch nlohmann/json
include(FetchContent)
FetchContent_Declare(
    json
    GIT_REPOSITORY https://github.com/nlohmann/json.git
    GIT_TAG v3.11.3
)
FetchContent_MakeAvailable(json)

add_executable(video-capture-mcp
    src/main.cpp
    src/mcp_server.cpp
    src/camera.mm
)

target_link_libraries(video-capture-mcp PRIVATE
    nlohmann_json::nlohmann_json
    "-framework AVFoundation"
    "-framework CoreMedia"
    "-framework CoreVideo"
    "-framework Foundation"
    "-framework ImageIO"
    "-framework CoreGraphics"
    "-framework UniformTypeIdentifiers"
)

target_include_directories(video-capture-mcp PRIVATE src)
