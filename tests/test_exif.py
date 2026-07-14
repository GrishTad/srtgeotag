from datetime import datetime
from pathlib import Path

import pytest
from PIL import ExifTags, Image

from srtgeotag.exif import write_exif
from srtgeotag.srt import TelemetryPoint


@pytest.mark.parametrize("extension", ["jpg", "png", "webp"])
def test_write_exif_supported_formats(tmp_path: Path, extension: str) -> None:
    path = tmp_path / f"frame.{extension}"
    Image.new("RGB", (16, 16), "red").save(path)
    point = TelemetryPoint(
        1, 0.0, 0.033, captured_at=datetime(2026, 4, 14, 8, 48, 5, 409000),
        latitude=-40.2, longitude=44.5, absolute_altitude=1344.2,
        relative_altitude=134.0, iso=110, shutter="1/1600.0", aperture=1.7,
        focal_length=24.0,
    )
    write_exif(path, point)
    with Image.open(path) as image:
        exif = image.getexif()
        assert exif[ExifTags.Base.Software] == "srtgeotag"
        assert '"relative_altitude":134.0' in exif[ExifTags.Base.ImageDescription]
        gps = exif.get_ifd(ExifTags.IFD.GPSInfo)
        assert gps[1] == "S"
        assert gps[3] == "E"
