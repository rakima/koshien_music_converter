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
        f"alimiter=limit={limiter_linear:.6f}:level=false"
    )


def target_peak_linear(settings: ArrangementSettings) -> float:
    return math.pow(10, settings.target_peak_dbfs / 20)


def build_mix_filter(settings: ArrangementSettings) -> str:
    """生成したラッパと太鼓だけをまとめ、最後にマスタリングする。"""
    mastering = build_mastering_filter(settings)
    return (
        "[0:a]highpass=f=160,"
        f"equalizer=f=2500:t=q:w=1:g={settings.brass_presence_db},"
        f"equalizer=f=4500:t=q:w=1:g={settings.brass_brightness_db},"
        "acompressor=threshold=-24dB:ratio=3:attack=8:release=45:makeup=2,"
        f"volume={settings.brass_volume}[brass];"
        "[1:a]"
        f"equalizer=f=90:t=q:w=1:g={settings.drum_body_db},"
        "equalizer=f=2400:t=q:w=1:g=2,"
        "acompressor=threshold=-20dB:ratio=4:attack=3:release=55:makeup=1.5,"
        f"volume={settings.generated_drum_volume}[drums];"
        "[brass][drums]amix=inputs=2:duration=longest:normalize=0,"
        f"{mastering}[out]"
    )


def parse_max_volume(lines: list[str]) -> float | None:
    for line in lines:
        match = re.search(r"max_volume:\s*(-?(?:\d+(?:\.\d+)?|inf))\s*dB", line)
        if match:
            return float(match.group(1))
    return None


def peak_is_within_ceiling(
    measured_dbfs: float,
    target_dbfs: float,
    *,
    tolerance_db: float = 0.5,
) -> bool:
    return measured_dbfs <= target_dbfs + tolerance_db
