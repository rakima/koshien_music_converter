import pytest

from koshien_music_converter.config import ArrangementSettings
from koshien_music_converter.mixing import (
    build_mix_filter,
    build_mastering_filter,
    parse_max_volume,
    peak_is_within_ceiling,
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
    assert "alimiter=limit=0.891251:level=false" in audio_filter


def test_target_peak_is_minus_one_dbfs() -> None:
    assert target_peak_linear(ArrangementSettings()) == pytest.approx(0.891251, rel=1e-5)


def test_mix_filter_uses_configured_part_volumes() -> None:
    settings = ArrangementSettings(
        brass_volume=1.2,
        generated_drum_volume=1.1,
    )

    audio_filter = build_mix_filter(settings)

    assert "equalizer=f=2500:t=q:w=1:g=4.0" in audio_filter
    assert "volume=1.2[brass]" in audio_filter
    assert "equalizer=f=90:t=q:w=1:g=5.0" in audio_filter
    assert "volume=1.1[drums]" in audio_filter
    assert "amix=inputs=2" in audio_filter
    assert "aecho" not in audio_filter
    assert "original" not in audio_filter
    assert "accompaniment" not in audio_filter
    assert "vocals" not in audio_filter


def test_parse_max_volume() -> None:
    lines = [
        "[Parsed_volumedetect_0] mean_volume: -15.2 dB",
        "[Parsed_volumedetect_0] max_volume: -1.0 dB",
    ]

    assert parse_max_volume(lines) == -1.0


def test_peak_ceiling_allows_only_small_encoding_difference() -> None:
    assert peak_is_within_ceiling(-0.9, -1.0)
    assert not peak_is_within_ceiling(-0.4, -1.0)
