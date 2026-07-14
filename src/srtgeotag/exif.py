"""Write standard EXIF GPS/camera tags plus the full telemetry payload."""

from __future__ import annotations

import json
from fractions import Fraction
from pathlib import Path
from typing import Optional, Tuple

from PIL import ExifTags, Image, TiffImagePlugin

from .srt import TelemetryPoint


def _rational(value: float, denominator: int = 1_000_000) -> TiffImagePlugin.IFDRational:
    fraction = Fraction(value).limit_denominator(denominator)
    return TiffImagePlugin.IFDRational(fraction.numerator, fraction.denominator)


def _dms(value: float) -> Tuple[TiffImagePlugin.IFDRational, ...]:
    absolute = abs(value)
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60
    minutes = int(minutes_float)
    seconds = (minutes_float - minutes) * 60
    return (_rational(degrees), _rational(minutes), _rational(seconds))


def _exposure_time(shutter: Optional[str]) -> Optional[TiffImagePlugin.IFDRational]:
    if not shutter:
        return None
    try:
        if "/" in shutter:
            numerator, denominator = shutter.split("/", 1)
            return _rational(float(numerator) / float(denominator))
        return _rational(float(shutter))
    except (ValueError, ZeroDivisionError):
        return None


def telemetry_dict(point: TelemetryPoint) -> dict:
    """Return a JSON-serializable representation of a telemetry point."""
    return {
        "srt_index": point.index,
        "video_time_seconds": point.start,
        "frame_count": point.frame_count,
        "captured_at": point.captured_at.isoformat(timespec="milliseconds")
        if point.captured_at else None,
        "latitude": point.latitude,
        "longitude": point.longitude,
        "relative_altitude": point.relative_altitude,
        "absolute_altitude": point.absolute_altitude,
        "iso": point.iso,
        "shutter": point.shutter,
        "aperture": point.aperture,
        "exposure_value": point.exposure_value,
        "focal_length": point.focal_length,
        "color_mode": point.color_mode,
        "color_temperature": point.color_temperature,
        **point.extra,
    }


def write_exif(path: Path, point: TelemetryPoint) -> None:
    """Embed telemetry in an image using Pillow (no ExifTool required)."""
    with Image.open(path) as image:
        exif = image.getexif()
        payload = json.dumps(telemetry_dict(point), separators=(",", ":"), ensure_ascii=True)
        exif[ExifTags.Base.Software] = "srtgeotag"
        exif[ExifTags.Base.ImageDescription] = payload

        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        exif_ifd[ExifTags.Base.UserComment] = b"ASCII\x00\x00\x00" + payload.encode("ascii")
        if point.captured_at:
            timestamp = point.captured_at.strftime("%Y:%m:%d %H:%M:%S")
            exif_ifd[ExifTags.Base.DateTimeOriginal] = timestamp
            exif_ifd[ExifTags.Base.DateTimeDigitized] = timestamp
            exif[ExifTags.Base.DateTime] = timestamp
            milliseconds = point.captured_at.strftime("%f").rstrip("0") or "0"
            exif_ifd[ExifTags.Base.SubsecTimeOriginal] = milliseconds
        if point.iso is not None:
            # EXIF 2.3 calls tag 34855 PhotographicSensitivity; Pillow keeps
            # the older, equivalent enum name for broad version compatibility.
            exif_ifd[ExifTags.Base.ISOSpeedRatings] = point.iso
        if point.aperture is not None:
            exif_ifd[ExifTags.Base.FNumber] = _rational(point.aperture)
        if point.focal_length is not None:
            exif_ifd[ExifTags.Base.FocalLength] = _rational(point.focal_length)
        exposure = _exposure_time(point.shutter)
        if exposure is not None:
            exif_ifd[ExifTags.Base.ExposureTime] = exposure
        if point.exposure_value is not None:
            exif_ifd[ExifTags.Base.ExposureBiasValue] = _rational(point.exposure_value)
        exif[ExifTags.IFD.Exif] = exif_ifd

        if point.latitude is not None and point.longitude is not None:
            gps = {
                0: b"\x02\x03\x00\x00",
                1: "N" if point.latitude >= 0 else "S",
                2: _dms(point.latitude),
                3: "E" if point.longitude >= 0 else "W",
                4: _dms(point.longitude),
            }
            if point.absolute_altitude is not None:
                gps[5] = 0 if point.absolute_altitude >= 0 else 1
                gps[6] = _rational(abs(point.absolute_altitude))
            exif[ExifTags.IFD.GPSInfo] = gps

        # TIFF uses its native IFD writer; other formats carry a serialized
        # EXIF block. Passing the native object preserves nested GPS in TIFF.
        save_options = {"tiffinfo": exif} if image.format == "TIFF" else {"exif": exif}
        if image.format == "JPEG":
            save_options.update(quality="keep", subsampling="keep")
        image.save(path, format=image.format, **save_options)
