from pathlib import Path

import pytest

from koshien_music_converter.config import ConversionConfig
from koshien_music_converter.errors import ConversionError


@pytest.fixture
def valid_config(tmp_path: Path) -> ConversionConfig:
    source = tmp_path / "input.mp3"
    source.touch()
    soundfont = tmp_path / "brass.sf2"
    soundfont.touch()
    return ConversionConfig(source, tmp_path / "output.mp3", 2, 12, soundfont)


def test_duration(valid_config: ConversionConfig) -> None:
    assert valid_config.duration == 10
    valid_config.validate()


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (-1, 10, "開始秒"),
        (10, 10, "終了秒"),
        (0, 31, "30秒以内"),
    ],
)
def test_invalid_range(
    valid_config: ConversionConfig, start: float, end: float, message: str
) -> None:
    config = ConversionConfig(
        valid_config.input_path,
        valid_config.output_path,
        start,
        end,
        valid_config.soundfont_path,
    )
    with pytest.raises(ConversionError, match=message):
        config.validate()


def test_output_must_be_mp3(valid_config: ConversionConfig) -> None:
    config = ConversionConfig(
        valid_config.input_path,
        valid_config.output_path.with_suffix(".wav"),
        valid_config.start_seconds,
        valid_config.end_seconds,
        valid_config.soundfont_path,
    )
    with pytest.raises(ConversionError, match="拡張子"):
        config.validate()

