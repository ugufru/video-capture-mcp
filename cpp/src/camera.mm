#import <AVFoundation/AVFoundation.h>
#import <CoreGraphics/CoreGraphics.h>
#import <CoreMedia/CoreMedia.h>
#import <ImageIO/ImageIO.h>
#import <Foundation/Foundation.h>
#import <UniformTypeIdentifiers/UniformTypeIdentifiers.h>

#include "camera.h"

#include <chrono>
#include <filesystem>
#include <stdexcept>
#include <thread>

// ── helpers ──────────────────────────────────────────────────────────────

static std::string nsstring_to_std(NSString* s) {
    return s ? std::string([s UTF8String]) : "";
}

static std::string temp_dir() {
    NSString* home = NSHomeDirectory();
    std::string dir = nsstring_to_std(home) + "/.tmp/video-capture-mcp";
    std::filesystem::create_directories(dir);
    return dir;
}

static NSArray<AVCaptureDevice*>* get_devices() {
    AVCaptureDeviceDiscoverySession* session =
        [AVCaptureDeviceDiscoverySession
            discoverySessionWithDeviceTypes:@[
                AVCaptureDeviceTypeBuiltInWideAngleCamera,
                AVCaptureDeviceTypeExternal
            ]
            mediaType:AVMediaTypeVideo
            position:AVCaptureDevicePositionUnspecified];
    return session.devices;
}

static std::vector<uint8_t> sample_buffer_to_png(CMSampleBufferRef buf) {
    CVImageBufferRef imageBuffer = CMSampleBufferGetImageBuffer(buf);
    CVPixelBufferLockBaseAddress(imageBuffer, kCVPixelBufferLock_ReadOnly);

    size_t w = CVPixelBufferGetWidth(imageBuffer);
    size_t h = CVPixelBufferGetHeight(imageBuffer);
    size_t bpr = CVPixelBufferGetBytesPerRow(imageBuffer);
    void* base = CVPixelBufferGetBaseAddress(imageBuffer);

    CGColorSpaceRef cs = CGColorSpaceCreateDeviceRGB();
    CGContextRef ctx = CGBitmapContextCreate(
        base, w, h, 8, bpr, cs,
        kCGBitmapByteOrder32Little | kCGImageAlphaPremultipliedFirst);

    CGImageRef cgImage = CGBitmapContextCreateImage(ctx);

    NSMutableData* pngData = [NSMutableData data];
    CGImageDestinationRef dest =
        CGImageDestinationCreateWithData((__bridge CFMutableDataRef)pngData,
                                         (__bridge CFStringRef)UTTypePNG.identifier, 1, nil);
    CGImageDestinationAddImage(dest, cgImage, nil);
    CGImageDestinationFinalize(dest);

    std::vector<uint8_t> result((uint8_t*)pngData.bytes,
                                (uint8_t*)pngData.bytes + pngData.length);

    CFRelease(dest);
    CGImageRelease(cgImage);
    CGContextRelease(ctx);
    CGColorSpaceRelease(cs);
    CVPixelBufferUnlockBaseAddress(imageBuffer, kCVPixelBufferLock_ReadOnly);

    return result;
}

// ── Synchronous capture delegate ─────────────────────────────────────────

@interface FrameGrabber : NSObject <AVCaptureVideoDataOutputSampleBufferDelegate>
@property (nonatomic) int framesToSkip;
@property (nonatomic) int framesSkipped;
@property (nonatomic) bool captured;
@property (nonatomic) CMSampleBufferRef sampleBuffer;
@end

@implementation FrameGrabber

- (void)captureOutput:(AVCaptureOutput*)output
    didOutputSampleBuffer:(CMSampleBufferRef)buf
       fromConnection:(AVCaptureConnection*)connection {
    if (self.framesSkipped < self.framesToSkip) {
        self.framesSkipped++;
        return;
    }
    if (!self.captured) {
        self.sampleBuffer = buf;
        CFRetain(buf);
        self.captured = true;
    }
}

- (void)dealloc {
    if (self.sampleBuffer) {
        CFRelease(self.sampleBuffer);
    }
}

@end

// ── Video recording delegate ─────────────────────────────────────────────

@interface VideoRecorder : NSObject <AVCaptureVideoDataOutputSampleBufferDelegate>
@property (nonatomic, strong) AVAssetWriter* writer;
@property (nonatomic, strong) AVAssetWriterInput* writerInput;
@property (nonatomic, strong) AVAssetWriterInputPixelBufferAdaptor* adaptor;
@property (nonatomic) bool started;
@property (nonatomic) int frameCount;
@property (nonatomic) int totalFramesNeeded;
@property (nonatomic) bool done;
@property (nonatomic) double fps;
@property (nonatomic) bool captureKeyframes;
@property (nonatomic) NSMutableArray<NSData*>* keyframePNGs;
@property (nonatomic) CMTime startTime;
@end

@implementation VideoRecorder

- (instancetype)init {
    self = [super init];
    if (self) {
        _keyframePNGs = [NSMutableArray array];
    }
    return self;
}

- (void)captureOutput:(AVCaptureOutput*)output
    didOutputSampleBuffer:(CMSampleBufferRef)buf
       fromConnection:(AVCaptureConnection*)connection {
    if (self.done) return;

    CMTime timestamp = CMSampleBufferGetPresentationTimeStamp(buf);

    if (!self.started) {
        [self.writer startSessionAtSourceTime:timestamp];
        self.startTime = timestamp;
        self.started = true;
    }

    if (self.writerInput.readyForMoreMediaData) {
        CVPixelBufferRef pb = CMSampleBufferGetImageBuffer(buf);
        CMTime frameTime = CMTimeMake(self.frameCount, (int32_t)self.fps);
        [self.adaptor appendPixelBuffer:pb
                   withPresentationTime:frameTime];
        self.frameCount++;

        // Capture keyframes at evenly-spaced intervals
        if (self.captureKeyframes && self.totalFramesNeeded > 0) {
            int interval = self.totalFramesNeeded / 5;
            if (interval < 1) interval = 1;
            if (self.frameCount % interval == 0 &&
                (int)self.keyframePNGs.count < 5) {
                auto png = sample_buffer_to_png(buf);
                [self.keyframePNGs addObject:
                    [NSData dataWithBytes:png.data() length:png.size()]];
            }
        }

        if (self.frameCount >= self.totalFramesNeeded) {
            self.done = true;
        }
    }
}

@end

// ── Public API ───────────────────────────────────────────────────────────

std::vector<CameraInfo> list_cameras() {
    @autoreleasepool {
        NSArray<AVCaptureDevice*>* devices = get_devices();
        std::vector<CameraInfo> result;

        for (NSUInteger i = 0; i < devices.count; i++) {
            AVCaptureDevice* dev = devices[i];
            CameraInfo info;
            info.index = (int)i;
            info.name = nsstring_to_std(dev.localizedName);
            info.unique_id = nsstring_to_std(dev.uniqueID);
            info.available = true;

            // Get active format dimensions
            CMFormatDescriptionRef fmt = dev.activeFormat.formatDescription;
            CMVideoDimensions dims =
                CMVideoFormatDescriptionGetDimensions(fmt);
            info.width = dims.width;
            info.height = dims.height;

            result.push_back(info);
        }
        return result;
    }
}

CaptureResult capture_photo(int device_index, int width, int height) {
    @autoreleasepool {
        NSArray<AVCaptureDevice*>* devices = get_devices();
        if (device_index < 0 || device_index >= (int)devices.count) {
            throw std::runtime_error("Invalid device index: " +
                                     std::to_string(device_index));
        }

        AVCaptureDevice* device = devices[device_index];
        NSError* error = nil;

        AVCaptureDeviceInput* input =
            [AVCaptureDeviceInput deviceInputWithDevice:device error:&error];
        if (error) {
            throw std::runtime_error(
                "Cannot open camera: " +
                nsstring_to_std(error.localizedDescription));
        }

        AVCaptureVideoDataOutput* output =
            [[AVCaptureVideoDataOutput alloc] init];
        output.videoSettings = @{
            (NSString*)kCVPixelBufferPixelFormatTypeKey :
                @(kCVPixelFormatType_32BGRA)
        };

        FrameGrabber* grabber = [[FrameGrabber alloc] init];
        grabber.framesToSkip = 5;  // warm-up frames
        dispatch_queue_t queue =
            dispatch_queue_create("capture", DISPATCH_QUEUE_SERIAL);
        [output setSampleBufferDelegate:grabber queue:queue];

        AVCaptureSession* session = [[AVCaptureSession alloc] init];

        // Set resolution preset if requested
        if (width > 1280 || height > 720) {
            session.sessionPreset = AVCaptureSessionPreset1920x1080;
        } else if (width > 640 || height > 480) {
            session.sessionPreset = AVCaptureSessionPreset1280x720;
        } else if (width > 0 && height > 0) {
            session.sessionPreset = AVCaptureSessionPreset640x480;
        } else {
            session.sessionPreset = AVCaptureSessionPresetHigh;
        }

        [session addInput:input];
        [session addOutput:output];
        [session startRunning];

        // Wait for capture (up to 5 seconds)
        auto deadline = std::chrono::steady_clock::now() +
                        std::chrono::seconds(5);
        while (!grabber.captured &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(10));
        }

        [session stopRunning];

        if (!grabber.captured) {
            throw std::runtime_error("Timeout waiting for frame");
        }

        auto png = sample_buffer_to_png(grabber.sampleBuffer);

        CVImageBufferRef ib =
            CMSampleBufferGetImageBuffer(grabber.sampleBuffer);
        CaptureResult result;
        result.png_data = std::move(png);
        result.width = (int)CVPixelBufferGetWidth(ib);
        result.height = (int)CVPixelBufferGetHeight(ib);
        result.camera_name = nsstring_to_std(device.localizedName);

        return result;
    }
}

VideoResult record_video(int device_index, double duration_seconds,
                         double fps, bool return_frames) {
    @autoreleasepool {
        duration_seconds = std::min(duration_seconds, 30.0);

        NSArray<AVCaptureDevice*>* devices = get_devices();
        if (device_index < 0 || device_index >= (int)devices.count) {
            throw std::runtime_error("Invalid device index: " +
                                     std::to_string(device_index));
        }

        AVCaptureDevice* device = devices[device_index];
        NSError* error = nil;

        AVCaptureDeviceInput* input =
            [AVCaptureDeviceInput deviceInputWithDevice:device error:&error];
        if (error) {
            throw std::runtime_error(
                "Cannot open camera: " +
                nsstring_to_std(error.localizedDescription));
        }

        AVCaptureVideoDataOutput* output =
            [[AVCaptureVideoDataOutput alloc] init];
        output.videoSettings = @{
            (NSString*)kCVPixelBufferPixelFormatTypeKey :
                @(kCVPixelFormatType_32BGRA)
        };

        AVCaptureSession* session = [[AVCaptureSession alloc] init];
        session.sessionPreset = AVCaptureSessionPresetHigh;
        [session addInput:input];
        [session addOutput:output];

        // Set up asset writer
        std::string dir = temp_dir();
        auto now = std::chrono::system_clock::now();
        auto ts = std::chrono::duration_cast<std::chrono::seconds>(
                      now.time_since_epoch()).count();
        std::string path = dir + "/recording_" + std::to_string(ts) + ".mp4";
        NSURL* url = [NSURL fileURLWithPath:
            [NSString stringWithUTF8String:path.c_str()]];

        AVAssetWriter* writer =
            [[AVAssetWriter alloc] initWithURL:url
                                      fileType:AVFileTypeMPEG4
                                         error:&error];
        if (error) {
            throw std::runtime_error(
                "Cannot create writer: " +
                nsstring_to_std(error.localizedDescription));
        }

        // Get dimensions from device
        CMFormatDescriptionRef fmt = device.activeFormat.formatDescription;
        CMVideoDimensions dims =
            CMVideoFormatDescriptionGetDimensions(fmt);

        NSDictionary* outputSettings = @{
            AVVideoCodecKey : AVVideoCodecTypeH264,
            AVVideoWidthKey : @(dims.width),
            AVVideoHeightKey : @(dims.height),
        };

        AVAssetWriterInput* writerInput =
            [AVAssetWriterInput assetWriterInputWithMediaType:AVMediaTypeVideo
                                              outputSettings:outputSettings];
        writerInput.expectsMediaDataInRealTime = YES;

        AVAssetWriterInputPixelBufferAdaptor* adaptor =
            [AVAssetWriterInputPixelBufferAdaptor
                assetWriterInputPixelBufferAdaptorWithAssetWriterInput:writerInput
                sourcePixelBufferAttributes:nil];

        [writer addInput:writerInput];
        [writer startWriting];

        // Set up recorder delegate
        VideoRecorder* recorder = [[VideoRecorder alloc] init];
        recorder.writer = writer;
        recorder.writerInput = writerInput;
        recorder.adaptor = adaptor;
        recorder.fps = fps;
        recorder.totalFramesNeeded = (int)(duration_seconds * fps);
        recorder.captureKeyframes = return_frames;

        dispatch_queue_t queue =
            dispatch_queue_create("record", DISPATCH_QUEUE_SERIAL);
        [output setSampleBufferDelegate:recorder queue:queue];

        [session startRunning];

        // Wait for recording to complete
        auto deadline = std::chrono::steady_clock::now() +
                        std::chrono::seconds((int)duration_seconds + 5);
        while (!recorder.done &&
               std::chrono::steady_clock::now() < deadline) {
            std::this_thread::sleep_for(std::chrono::milliseconds(50));
        }

        [session stopRunning];
        [writerInput markAsFinished];

        // Finalize writer synchronously
        dispatch_semaphore_t sem = dispatch_semaphore_create(0);
        [writer finishWritingWithCompletionHandler:^{
            dispatch_semaphore_signal(sem);
        }];
        dispatch_semaphore_wait(sem, dispatch_time(DISPATCH_TIME_NOW,
                                                    5 * NSEC_PER_SEC));

        VideoResult result;
        result.file_path = path;
        result.frame_count = recorder.frameCount;
        result.camera_name = nsstring_to_std(device.localizedName);

        if (return_frames) {
            for (NSData* png in recorder.keyframePNGs) {
                std::vector<uint8_t> v((uint8_t*)png.bytes,
                                       (uint8_t*)png.bytes + png.length);
                result.keyframe_pngs.push_back(std::move(v));
            }
        }

        return result;
    }
}
