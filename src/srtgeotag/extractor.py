"""Fast FFmpeg-backed frame extraction and telemetry synchronization."""

from __future__ import annotations

import bisect
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Sequence, Union

from .exif import write_exif
from .srt import TelemetryPoint, parse_srt

PathLike = Union[str, Path]
ProgressCallback = Callable[[str, float], None]
SUPPORTED_FORMATS = {"jpg": "jpg", "jpeg": "jpg", "png": "png", "webp": "webp"}


@dataclass(frozen=True)
class ExtractionResult:
    video: Path
    srt: Path
    output_dir: Path
    frames: Sequence[Path]


def matching_srt(video: PathLike) -> Path:
    """Find a same-stem .srt file, case-insensitively."""
    video = Path(video)
    direct = video.with_suffix(".srt")
    if direct.exists():
        return direct
    wanted = video.stem.casefold()
    for candidate in video.parent.iterdir():
        if candidate.is_file() and candidate.suffix.casefold() == ".srt" and candidate.stem.casefold() == wanted:
            return candidate
    raise FileNotFoundError(f"No same-name SRT file found for {video}")


def _nearest(points: Sequence[TelemetryPoint], starts: Sequence[float], timestamp: float) -> TelemetryPoint:
    position = bisect.bisect_left(starts, timestamp)
    if position == 0:
        return points[0]
    if position == len(points):
        return points[-1]
    before, after = points[position - 1], points[position]
    return before if timestamp - before.start <= after.start - timestamp else after


def extract_video(
    video: PathLike,
    output_dir: PathLike,
    *,
    fps: float = 1.0,
    image_format: str = "jpg",
    srt: Optional[PathLike] = None,
    ffmpeg: str = "ffmpeg",
    overwrite: bool = False,
    progress: Optional[ProgressCallback] = None,
) -> ExtractionResult:
    """Extract frames from one video and embed nearest-in-time SRT telemetry."""
    video_path = Path(video).expanduser().resolve()
    if not video_path.is_file():
        raise FileNotFoundError(f"Video does not exist: {video_path}")
    if fps <= 0:
        raise ValueError("fps must be greater than zero")
    fmt = SUPPORTED_FORMATS.get(image_format.lower().lstrip("."))
    if fmt is None:
        raise ValueError(f"Unsupported image format: {image_format}")
    srt_path = Path(srt).expanduser().resolve() if srt else matching_srt(video_path).resolve()
    points = parse_srt(srt_path)
    starts = [point.start for point in points]
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)

    if shutil.which(ffmpeg) is None:
        raise FileNotFoundError("FFmpeg was not found. Install it and ensure 'ffmpeg' is on PATH.")

    with tempfile.TemporaryDirectory(prefix=".srtgeotag-", dir=destination) as temporary:
        temp_dir = Path(temporary)
        pattern = temp_dir / f"%06d.{fmt}"
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-progress", "pipe:1",
            "-stats_period", "0.25", "-i", str(video_path),
            "-map", "0:v:0", "-vf", f"fps={fps:.12g}", "-fps_mode", "vfr",
        ]
        if fmt == "jpg":
            command.extend(["-q:v", "2"])
        command.extend(["-start_number", "1", str(pattern)])
        extraction_label = f"{video_path.name}: extracting"
        if progress:
            progress(extraction_label, 0.0)
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert process.stdout is not None
        duration = max(points[-1].end, 0.001)
        for line in process.stdout:
            key, separator, value = line.strip().partition("=")
            if progress and separator and key == "out_time_us":
                try:
                    progress(extraction_label, min(float(value) / 1_000_000 / duration, 0.99))
                except ValueError:
                    pass
        stderr = process.stderr.read() if process.stderr else ""
        return_code = process.wait()
        if return_code:
            detail = stderr.strip().splitlines()[-1] if stderr.strip() else "unknown FFmpeg error"
            raise RuntimeError(f"FFmpeg failed while extracting {video_path.name}: {detail}")
        if progress:
            progress(extraction_label, 1.0)

        generated = sorted(temp_dir.glob(f"*.{fmt}"))
        if not generated:
            raise RuntimeError(f"FFmpeg extracted no frames from {video_path.name}")
        targets = [destination / frame.name for frame in generated]
        conflicts = [target for target in targets if target.exists()]
        if conflicts and not overwrite:
            raise FileExistsError(f"Output already exists: {conflicts[0]} (use overwrite=True)")

        tagging_label = f"{video_path.name}: tagging"
        if progress:
            progress(tagging_label, 0.0)
        for number, (frame, target) in enumerate(zip(generated, targets), start=1):
            timestamp = (number - 1) / fps
            write_exif(frame, _nearest(points, starts, timestamp))
            frame.replace(target)
            if progress:
                progress(tagging_label, number / len(generated))

    return ExtractionResult(video_path, srt_path, destination, tuple(targets))


def extract_videos(
    videos: Iterable[PathLike],
    output_dir: PathLike,
    **kwargs: object,
) -> List[ExtractionResult]:
    """Extract one or many videos; batches get one output subdirectory per video."""
    paths = [Path(video) for video in videos]
    if not paths:
        raise ValueError("At least one video is required")
    root = Path(output_dir)
    multiple = len(paths) > 1
    return [extract_video(video, root / video.stem if multiple else root, **kwargs) for video in paths]
