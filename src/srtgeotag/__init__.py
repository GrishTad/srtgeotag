"""Extract video frames and attach matching DJI SRT telemetry as EXIF."""

from .extractor import ExtractionResult, extract_video, extract_videos
from .srt import TelemetryPoint, parse_srt

__all__ = [
    "ExtractionResult",
    "TelemetryPoint",
    "extract_video",
    "extract_videos",
    "parse_srt",
]
__version__ = "0.1.0"

