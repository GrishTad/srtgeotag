"""DJI subtitle telemetry parser."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

_BLOCK_RE = re.compile(
    r"(?ms)^\s*(\d+)\s*\r?\n"
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*-->\s*"
    r"(\d{2}:\d{2}:\d{2}[,.]\d{3})\s*\r?\n"
    r"(.*?)(?=\r?\n\s*\r?\n|\Z)"
)
_PAIR_RE = re.compile(r"\[\s*([^:\]]+)\s*:\s*([^\]]*)\]")
_ALT_RE = re.compile(
    r"rel_alt\s*:\s*([-+]?\d+(?:\.\d+)?)\s+abs_alt\s*:\s*([-+]?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_FRAME_RE = re.compile(r"FrameCnt\s*:\s*(\d+)", re.IGNORECASE)
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def _seconds(value: str) -> float:
    hours, minutes, seconds = value.replace(",", ".").split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def _float(value: Optional[str]) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value.strip())
    except ValueError:
        return None


def _int(value: Optional[str]) -> Optional[int]:
    number = _float(value)
    return int(number) if number is not None else None


@dataclass(frozen=True)
class TelemetryPoint:
    """Telemetry associated with one subtitle/video frame."""

    index: int
    start: float
    end: float
    frame_count: Optional[int] = None
    captured_at: Optional[datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    relative_altitude: Optional[float] = None
    absolute_altitude: Optional[float] = None
    iso: Optional[int] = None
    shutter: Optional[str] = None
    aperture: Optional[float] = None
    exposure_value: Optional[float] = None
    focal_length: Optional[float] = None
    color_mode: Optional[str] = None
    color_temperature: Optional[int] = None
    extra: Dict[str, str] = field(default_factory=dict)


def parse_srt(path: Union[str, Path]) -> List[TelemetryPoint]:
    """Parse a DJI SRT file, tolerating CRLF, HTML wrappers, and extra fields."""
    path = Path(path)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    points: List[TelemetryPoint] = []

    for match in _BLOCK_RE.finditer(text):
        body = html.unescape(re.sub(r"<[^>]+>", "", match.group(4)))
        pairs = {key.strip().lower(): value.strip() for key, value in _PAIR_RE.findall(body)}
        altitude = _ALT_RE.search(body)
        date_match = _DATE_RE.search(body)
        frame_match = _FRAME_RE.search(body)
        captured_at = None
        if date_match:
            try:
                captured_at = datetime.fromisoformat(date_match.group(0))
            except ValueError:
                pass

        known = {
            "iso", "shutter", "fnum", "ev", "focal_len", "latitude", "longitude",
            "rel_alt", "ct", "color_md",
        }
        points.append(
            TelemetryPoint(
                index=int(match.group(1)),
                start=_seconds(match.group(2)),
                end=_seconds(match.group(3)),
                frame_count=int(frame_match.group(1)) if frame_match else None,
                captured_at=captured_at,
                latitude=_float(pairs.get("latitude")),
                longitude=_float(pairs.get("longitude")),
                relative_altitude=_float(altitude.group(1)) if altitude else None,
                absolute_altitude=_float(altitude.group(2)) if altitude else None,
                iso=_int(pairs.get("iso")),
                shutter=pairs.get("shutter"),
                aperture=_float(pairs.get("fnum")),
                exposure_value=_float(pairs.get("ev")),
                focal_length=_float(pairs.get("focal_len")),
                color_mode=pairs.get("color_md"),
                color_temperature=_int(pairs.get("ct")),
                extra={key: value for key, value in pairs.items() if key not in known},
            )
        )

    if not points:
        raise ValueError(f"No valid subtitle telemetry blocks found in {path}")
    return points

