from __future__ import annotations

import math

from .config import ArrangementSettings


def build_mastering_filter(settings: ArrangementSettings) -> str:
    """最終ミックスを聴感音量とピークの両面から整える。"""
    limiter_linear = 10 ** (settings.target_peak_dbfs / 20)
    return (
        "acompressor="
        f"threshold={settings.compressor_threshold_db}dB:"
        f"ratio={settings.compressor_ratio}:"
        f"attack={settings.compressor_attack_ms}:"
        f"release={settings.compressor_release_ms},"
        "loudnorm="
        f"I={settings.target_loudness_lufs}:"
        f"LRA={settings.loudness_range}:"
        f"TP={settings.target_peak_dbfs},"
        f"alimiter=limit={limiter_linear:.6f}"
    )


def target_peak_linear(settings: ArrangementSettings) -> float:
    return math.pow(10, settings.target_peak_dbfs / 20)
