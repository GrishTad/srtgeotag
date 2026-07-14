from pathlib import Path

from srtgeotag.srt import parse_srt


def test_parse_dji_srt(tmp_path: Path) -> None:
    sample = tmp_path / "flight.srt"
    sample.write_text(
        "1\n00:00:00,000 --> 00:00:00,033\n"
        '<font size="28">FrameCnt: 1, DiffTime: 33ms\n'
        "2026-04-14 08:48:05.409\n"
        "[iso: 110] [shutter: 1/1600.0] [fnum: 1.7] [ev: -0.3] "
        "[color_md : default] [focal_len: 24.00] [latitude: -40.224150] "
        "[longitude: -44.552822] [rel_alt: 134.000 abs_alt: 1344.202] [ct: 5602] </font>\n",
        encoding="utf-8",
    )
    point = parse_srt(sample)[0]
    assert point.frame_count == 1
    assert point.start == 0
    assert point.latitude == -40.22415
    assert point.longitude == -44.552822
    assert point.relative_altitude == 134.0
    assert point.absolute_altitude == 1344.202
    assert point.iso == 110
    assert point.shutter == "1/1600.0"
    assert point.captured_at.microsecond == 409000

