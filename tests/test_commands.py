from unittest.mock import patch

import pytest

from koshien_music_converter.commands import require_command
from koshien_music_converter.errors import DependencyError


def test_require_command_returns_path() -> None:
    with patch("shutil.which", return_value="C:/tools/ffmpeg.exe"):
        assert require_command("ffmpeg") == "C:/tools/ffmpeg.exe"


def test_require_command_reports_missing_tool() -> None:
    with patch("shutil.which", return_value=None):
        with pytest.raises(DependencyError, match="ffmpeg"):
            require_command("ffmpeg")

