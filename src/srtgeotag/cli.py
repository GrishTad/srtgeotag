"""Command-line interface for srtgeotag."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Sequence, TextIO

from .extractor import SUPPORTED_FORMATS, extract_videos

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v"}


class _ConsoleProgress:
    """Small dependency-free terminal progress renderer."""

    def __init__(self, stream: TextIO = sys.stderr, width: int = 30) -> None:
        self.stream = stream
        self.width = width
        self._label: Optional[str] = None
        self._percent: Optional[int] = None

    def __call__(self, label: str, fraction: float) -> None:
        if self._label is not None and label != self._label:
            self.stream.write("\n")
        fraction = min(max(fraction, 0.0), 1.0)
        percent = round(fraction * 1000)
        if label == self._label and percent == self._percent:
            return
        self._label = label
        self._percent = percent
        filled = round(self.width * fraction)
        bar = "#" * filled + "-" * (self.width - filled)
        self.stream.write(f"\r{label} [{bar}] {fraction:6.1%}")
        if fraction >= 1.0:
            self.stream.write("\n")
            self._label = None
            self._percent = None
        self.stream.flush()


def _videos(values: Sequence[str]) -> List[Path]:
    found: List[Path] = []
    for value in values:
        path = Path(value).expanduser()
        if path.is_dir():
            found.extend(sorted(item for item in path.iterdir() if item.suffix.casefold() in VIDEO_EXTENSIONS))
        else:
            found.append(path)
    return found


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="srtgeotag",
        description="Extract video frames and geotag them from same-name DJI SRT files.",
    )
    parser.add_argument("videos", nargs="+", help="video file(s), or a directory of videos")
    parser.add_argument("-o", "--output", default="frames", help="output directory (default: frames)")
    rate = parser.add_mutually_exclusive_group()
    rate.add_argument("--fps", type=float, default=1.0, help="frames to extract per second (default: 1)")
    rate.add_argument("--interval", type=float, help="seconds between extracted frames (e.g. 2)")
    parser.add_argument("-f", "--format", choices=sorted(SUPPORTED_FORMATS), default="jpg", help="image format")
    parser.add_argument("--srt", help="explicit SRT path (only valid with one video)")
    parser.add_argument("--ffmpeg", default="ffmpeg", help="FFmpeg executable or path")
    parser.add_argument("--overwrite", action="store_true", help="replace existing frame files")
    parser.add_argument("--no-progress", action="store_true", help="disable progress bars")
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    videos = _videos(args.videos)
    if not videos:
        parser.error("no videos found")
    if args.srt and len(videos) != 1:
        parser.error("--srt can only be used with one video")
    fps = 1.0 / args.interval if args.interval is not None else args.fps
    if args.interval is not None and args.interval <= 0:
        parser.error("--interval must be greater than zero")
    if fps <= 0:
        parser.error("--fps must be greater than zero")

    try:
        progress = None if args.no_progress else _ConsoleProgress()
        results = extract_videos(
            videos, args.output, fps=fps, image_format=args.format, srt=args.srt,
            ffmpeg=args.ffmpeg, overwrite=args.overwrite, progress=progress,
        )
    except (FileNotFoundError, FileExistsError, ValueError, RuntimeError) as exc:
        print(f"srtgeotag: error: {exc}", file=sys.stderr)
        return 1
    for result in results:
        print(f"{result.video.name}: wrote {len(result.frames)} frame(s) to {result.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
