import pytest

from koshien_music_converter.config import ArrangementSettings
from koshien_music_converter.mixing import (
    build_mix_filter,
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


def test_mix_filter_uses_configured_part_volumes() -> None:
    settings = ArrangementSettings(
        brass_volume=1.2,
        generated_drum_volume=1.1,
        original_drum_volume=0.2,
        accompaniment_volume=0.15,
        vocal_volume=0,
    )

    audio_filter = build_mix_filter(settings)

    assert "[0:a]volume=1.2[brass]" in audio_filter
    assert "[1:a]volume=1.1[drums]" in audio_filter
    assert "[2:a]volume=0.2[original_drums]" in audio_filter
    assert "[accompaniment_raw]volume=0.15[accompaniment]" in audio_filter
    assert "[5:a]volume=0[vocals]" in audio_filter
    assert "amix=inputs=5" in audio_filter
