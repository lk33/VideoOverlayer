# Video Transcoding and Packaging Script

This script transcodes a given video file into multiple resolutions, applies HDR/SDR-specific modifications, and packages the outputs in DASH streamable format.

## Requirements

1. **FFmpeg**: A complete, cross-platform solution to record, convert and stream audio and video.
2. **Bento4**: A C++ class library and tools for dealing with MP4 files.

## Setup Instructions

1. **Install FFmpeg**:
   - For Windows: Download the executable from [FFmpeg website](https://ffmpeg.org/download.html) and add it to your system's PATH.
   - For macOS: `brew install ffmpeg`
   - For Ubuntu: `sudo apt-get install ffmpeg`
   ffmpeg-master-latest-win64-gpl-shared

2. **Install Bento4**:
   - Download and install Bento4 from [Bento4 website](https://www.bento4.com/).
   - Make sure `mp4dash` is available in your system's PATH.

3. **Install Python Requirements**:
   - Ensure you have Python installed. The script uses standard libraries.

## HDR check
```
ffprobe -v error -select_streams v:0 -show_entries stream=color_space,color_transfer,color_primaries -of default=noprint_wrappers=1:nokey=1 .\output.mp4
```

## Usage

To run the script, use the following command:

```
python transcode_and_package.py <path_to_video_file>
```
