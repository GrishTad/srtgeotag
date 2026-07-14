# srtgeotag

`srtgeotag` extracts still frames from drone video and embeds the matching DJI
SRT telemetry in each image. It works as both a Python library and a command-line tool.

## Features

- Single videos, multiple videos, or every video in a directory
- Automatic same-name SRT discovery, including `.SRT` on case-sensitive systems
- Sampling by frames per second or by time interval
- JPEG, PNG, and WebP output
- Standard EXIF GPS, altitude, capture time, ISO, exposure, aperture, and focal length
- Complete telemetry preserved as compact JSON in EXIF `ImageDescription` and `UserComment`
- Fast, single-pass extraction with FFmpeg; no ExifTool or source-FPS argument required
- Live progress bars for frame extraction and EXIF telemetry tagging

## Requirements and installation

Install [FFmpeg](https://ffmpeg.org/download.html) and make sure `ffmpeg` is on `PATH`, then:

```console
pip install srtgeotag
```

For local development:

```console
python -m pip install -e ".[dev]"
```

To install directly from a downloaded or cloned project folder:

```console
cd srtgeotag
python -m pip install .
srtgeotag --version
```

## CLI

The SRT is found beside each video by matching its filename stem.

```console
# One frame per second
srtgeotag DJI_0001.MP4 -o frames --fps 1 --format jpg

# One frame every two seconds
srtgeotag DJI_0001.MP4 -o frames --interval 2 --format png

# Several files (all frames go into the same directory)
srtgeotag DJI_0001.MP4 DJI_0002.MP4 -o frames --fps 0.5

# Optionally use one named subdirectory per video
srtgeotag DJI_0001.MP4 DJI_0002.MP4 -o frames --fps 0.5 --separate-directories

# Every supported video in a directory
srtgeotag ./flight -o frames --interval 5
```

Use `--overwrite` to replace existing numbered images. Progress is displayed by default;
use `--no-progress` when running in scripts or CI. Run `srtgeotag --help` for all options.

## Python API

```python
from srtgeotag import extract_video, extract_videos, parse_srt

result = extract_video(
    "DJI_0001.MP4",
    "frames",
    fps=0.5,                 # one image every two seconds
    image_format="jpg",
)
print(result.frames)

telemetry = parse_srt("DJI_0001.SRT")
print(telemetry[0].latitude, telemetry[0].longitude)
```

`extract_video()` accepts `srt=...` for an explicitly named subtitle and `ffmpeg=...`
for a custom executable path. By default, `extract_videos()` writes the entire batch
into one directory and prefixes filenames with each video's stem. Pass
`separate_directories=True` to create one named subdirectory per video.

## Telemetry mapping

Each output image is matched to the nearest SRT record using elapsed video time. This
avoids accumulated timing errors for fractional rates such as 29.97 fps. Latitude,
longitude, absolute altitude, capture time, ISO, shutter/exposure time, aperture,
exposure bias, and focal length use standard EXIF fields. DJI-only values such as
relative altitude, color mode, and color temperature remain available in the embedded
JSON payload.

## License

MIT

## About AutoWaypoints.com

This project is open-sourced by [AutoWaypoints.com](https://autowaypoints.com), a
DJI drone mission-planning platform for automated mapping, photogrammetry, 3D capture,
and Gaussian splatting workflows.
