# Changelog

This project follows [Semantic Versioning](https://semver.org/).

## 0.2.0 - 2026-07-14

- Write multi-video batch output into one directory by default
- Prefix batch frame names with the source video stem to prevent collisions
- Add `--separate-directories` and `separate_directories=True` for the previous layout

## 0.1.0 - 2026-07-13

- Initial Python API and command-line interface
- DJI SRT telemetry parsing
- FFmpeg-based batch frame extraction
- Native EXIF GPS, camera, time, and full telemetry metadata
- JPEG, PNG, and WebP output
