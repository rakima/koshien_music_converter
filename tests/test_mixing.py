import pytest

from koshien_music_converter.config import ArrangementSettings
from koshien_music_converter.mixing import (
    build_mastering_filter,
    target_peak_linear,
)


def test_mastering_filter_contains_loudness_compression_and_limiter() -> None:
    settings = ArrangementSettings(
        target_loudness_lufs=-13,
        target_peak_dbfs=-1,
        compressor_threshold_db=-20,
    )

    audio_filter = build_mastering_filter(settings)

    assert "acompressor=threshold=-20dB" in audio_filter
    assert "loudnorm=I=-13:LRA=9.0:TP=-1" in audio_filter
    assert "alimiter=limit=0.891251" in audio_filter


def test_target_peak_is_minus_one_dbfs() -> None:
    assert target_peak_linear(ArrangementSettings()) == pytest.approx(0.891251, rel=1e-5)
