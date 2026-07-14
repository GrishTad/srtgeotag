from io import StringIO

from srtgeotag.cli import _ConsoleProgress


def test_console_progress() -> None:
    stream = StringIO()
    progress = _ConsoleProgress(stream=stream, width=10)
    progress("video.mp4: extracting", 0.5)
    progress("video.mp4: extracting", 1.0)
    output = stream.getvalue()
    assert "[#####-----]  50.0%" in output
    assert "[##########] 100.0%" in output
    assert output.endswith("\n")
