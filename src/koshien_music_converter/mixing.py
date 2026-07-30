from __future__ import annotations

import math
import re

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


def build_mix_filter(settings: ArrangementSettings) -> str:
    """各ステムを設定された比率でまとめ、最後にマスタリングする。"""
    mastering = build_mastering_filter(settings)
    return (
        f"[0:a]volume={settings.brass_volume}[brass];"
        f"[1:a]volume={settings.generated_drum_volume}[drums];"
        f"[2:a]volume={settings.original_drum_volume}[original_drums];"
        "[3:a][4:a]amix=inputs=2:normalize=0[accompaniment_raw];"
        f"[accompaniment_raw]volume={settings.accompaniment_volume}"
        "[accompaniment];"
        f"[5:a]volume={settings.vocal_volume}[vocals];"
        "[brass][drums][original_drums][accompaniment][vocals]"
        "amix=inputs=5:duration=longest:normalize=0,"
        f"aecho=0.8:0.25:55:0.12,{mastering}[out]"
    )


def parse_max_volume(lines: list[str]) -> float | None:
    for line in lines:
        match = re.search(r"max_volume:\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB", line)
        if match:
            return float(match.group(1))
    return None
