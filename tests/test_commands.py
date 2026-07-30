from unittest.mock import MagicMock, patch

import pytest

from koshien_music_converter.commands import require_command, run_command
from koshien_music_converter.errors import DependencyError


def test_require_command_returns_path() -> None:
    with patch("shutil.which", return_value="C:/tools/ffmpeg.exe"):
        assert require_command("ffmpeg") == "C:/tools/ffmpeg.exe"


def test_require_command_reports_missing_tool() -> None:
    with patch("shutil.which", return_value=None):
        with pytest.raises(DependencyError, match="ffmpeg"):
            require_command("ffmpeg")


def test_run_command_returns_logged_output() -> None:
    process = MagicMock()
    process.stdout = iter(["first\n", "\n", "second\n"])
    process.wait.return_value = 0
    logs: list[str] = []

    with patch("subprocess.Popen", return_value=process):
        output = run_command(["tool", "arg"], logs.append)

    assert output == ["first", "second"]
    assert logs[-2:] == ["first", "second"]

