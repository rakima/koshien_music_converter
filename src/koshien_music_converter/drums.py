from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .errors import ConversionError, DependencyError

DEFAULT_BPM = 120.0


@dataclass(frozen=True)
class DrumEvent:
    time: float
    kind: str


def estimate_bpm(source: Path) -> float:
    try:
        import librosa
        import numpy as np
    except ImportError as exc:
        raise DependencyError(
            "BPM解析ライブラリを読み込めません。pip install -e . を実行してください。"
        ) from exc

    try:
        audio, sample_rate = librosa.load(source, sr=22050, mono=True)
        tempo, _beats = librosa.beat.beat_track(y=audio, sr=sample_rate)
        tempo_values = np.asarray(tempo).reshape(-1)
        if tempo_values.size == 0:
            return DEFAULT_BPM
        bpm = float(tempo_values[0])
        return bpm if math.isfinite(bpm) and 50 <= bpm <= 220 else DEFAULT_BPM
    except Exception as exc:
        raise ConversionError(f"BPMの解析に失敗しました: {exc}") from exc


def build_cheer_pattern(
    duration: float,
    bpm: float,
    *,
    cymbal_interval_bars: int = 4,
) -> list[DrumEvent]:
    """大太鼓と小太鼓を交互に置く安定した4拍パターン。"""
    beat_duration = 60 / bpm
    events: list[DrumEvent] = []
    bar_duration = beat_duration * 4
    bar_index = 0
    while (bar_start := bar_index * bar_duration) < duration:
        for beat_offset, kind in (
            (0.0, "odaiko_accent"),
            (1.0, "snare"),
            (2.0, "odaiko"),
            (3.0, "snare"),
        ):
            event_time = bar_start + beat_offset * beat_duration
            if event_time < duration:
                events.append(DrumEvent(event_time, kind))
        if bar_index % cymbal_interval_bars == 0:
            events.append(DrumEvent(bar_start, "cymbal"))
        bar_index += 1
    return events


def generate_cheer_drums(
    destination: Path,
    duration: float,
    bpm: float,
    *,
    sample_rate: int = 44100,
    cymbal_interval_bars: int = 4,
) -> int:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise DependencyError(
            "太鼓生成ライブラリを読み込めません。pip install -e . を実行してください。"
        ) from exc

    events = build_cheer_pattern(
        duration, bpm, cymbal_interval_bars=cymbal_interval_bars
    )
    audio = np.zeros(math.ceil(duration * sample_rate), dtype=np.float32)
    random = np.random.default_rng(2026)

    for event in events:
        start = round(event.time * sample_rate)
        if event.kind == "odaiko_accent":
            sound = _odaiko_sound(sample_rate, np, accent=True)
        elif event.kind == "odaiko":
            sound = _odaiko_sound(sample_rate, np, accent=False)
        elif event.kind == "snare":
            sound = _snare_sound(sample_rate, np, random)
        else:
            sound = _cymbal_sound(sample_rate, np, random)
        end = min(audio.size, start + sound.size)
        audio[start:end] += sound[: end - start]

    peak = float(np.max(np.abs(audio))) if audio.size else 0
    if peak <= 0:
        raise ConversionError("応援太鼓が無音になりました。")
    audio *= 0.88 / peak
    stereo = np.column_stack((audio, audio))
    sf.write(destination, stereo, sample_rate, subtype="PCM_16")
    return len(events)


def _odaiko_sound(sample_rate: int, np: object, *, accent: bool) -> object:
    duration = 0.28
    time = np.arange(round(sample_rate * duration)) / sample_rate
    frequency = 52 + 68 * np.exp(-time * 25)
    phase = 2 * np.pi * np.cumsum(frequency) / sample_rate
    body = np.sin(phase) * np.exp(-time * 13)
    overtone = np.sin(phase * 1.97) * np.exp(-time * 20) * 0.22
    attack = np.exp(-time * 95) * 0.48
    gain = 1.0 if accent else 0.78
    return ((body + overtone + attack) * gain).astype(np.float32)


def _snare_sound(sample_rate: int, np: object, random: object) -> object:
    duration = 0.14
    time = np.arange(round(sample_rate * duration)) / sample_rate
    noise = random.standard_normal(time.size)
    bright_noise = noise - np.roll(noise, 1)
    body = np.sin(2 * np.pi * 185 * time) * np.exp(-time * 32)
    return (
        (bright_noise * np.exp(-time * 30) * 0.24 + body * 0.18)
        .astype(np.float32)
    )


def _cymbal_sound(sample_rate: int, np: object, random: object) -> object:
    duration = 0.55
    time = np.arange(round(sample_rate * duration)) / sample_rate
    noise = random.standard_normal(time.size)
    bright_noise = noise - np.roll(noise, 1)
    return (bright_noise * np.exp(-time * 7) * 0.12).astype(np.float32)
