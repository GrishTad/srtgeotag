from pathlib import Path

import srtgeotag.extractor as extractor


def test_batch_uses_one_directory_and_video_prefixes(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_extract(video, output_dir, **kwargs):
        calls.append((Path(video), Path(output_dir), kwargs["filename_prefix"]))
        return object()

    monkeypatch.setattr(extractor, "extract_video", fake_extract)
    extractor.extract_videos(["DJI_0001.MP4", "DJI_0002.MP4"], tmp_path)

    assert calls == [
        (Path("DJI_0001.MP4"), tmp_path, "DJI_0001_"),
        (Path("DJI_0002.MP4"), tmp_path, "DJI_0002_"),
    ]


def test_batch_can_use_separate_directories(monkeypatch, tmp_path: Path) -> None:
    calls = []

    def fake_extract(video, output_dir, **kwargs):
        calls.append((Path(video), Path(output_dir), kwargs["filename_prefix"]))
        return object()

    monkeypatch.setattr(extractor, "extract_video", fake_extract)
    extractor.extract_videos(
        ["DJI_0001.MP4", "DJI_0002.MP4"], tmp_path, separate_directories=True
    )

    assert calls == [
        (Path("DJI_0001.MP4"), tmp_path / "DJI_0001", ""),
        (Path("DJI_0002.MP4"), tmp_path / "DJI_0002", ""),
    ]
