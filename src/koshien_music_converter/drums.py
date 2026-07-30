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


def build_cheer_pattern(duration: float, bpm: float) -> list[DrumEvent]:
    """4拍の固定応援パターンをイベント列にする。"""
    beat_duration = 60 / bpm
    events: list[DrumEvent] = []
    beat_index = 0
    while (time := beat_index * beat_duration) < duration:
        beat_in_bar = beat_index % 4
        events.append(
            DrumEvent(time, "kick" if beat_in_bar in (0, 2) else "clap")
        )
        if beat_index % 8 == 0:
            events.append(DrumEvent(time, "cymbal"))
        if beat_in_bar == 3:
            follow_up = time + beat_duration / 2
            if follow_up < duration:
                events.append(DrumEvent(follow_up, "kick"))
        beat_index += 1
    return events


def generate_cheer_drums(
    destination: Path,
    duration: float,
    bpm: float,
    *,
    sample_rate: int = 44100,
) -> int:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        raise DependencyError(
            "太鼓生成ライブラリを読み込めません。pip install -e . を実行してください。"
        ) from exc

    events = build_cheer_pattern(duration, bpm)
    audio = np.zeros(math.ceil(duration * sample_rate), dtype=np.float32)
    random = np.random.default_rng(2026)

    for event in events:
        start = round(event.time * sample_rate)
        if event.kind == "kick":
            sound = _kick_sound(sample_rate, np)
        elif event.kind == "clap":
            sound = _clap_sound(sample_rate, np, random)
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


def _kick_sound(sample_rate: int, np: object) -> object:
    duration = 0.32
    time = np.arange(round(sample_rate * duration)) / sample_rate
    frequency = 48 + 62 * np.exp(-time * 22)
    phase = 2 * np.pi * np.cumsum(frequency) / sample_rate
    body = np.sin(phase) * np.exp(-time * 10)
    attack = np.exp(-time * 70) * 0.35
    return (body + attack).astype(np.float32)


def _clap_sound(sample_rate: int, np: object, random: object) -> object:
    duration = 0.16
    time = np.arange(round(sample_rate * duration)) / sample_rate
    noise = random.standard_normal(time.size)
    bright_noise = noise - np.roll(noise, 1)
    envelope = np.exp(-time * 28) * (0.75 + 0.25 * np.sin(2 * np.pi * 32 * time))
    return (bright_noise * envelope * 0.28).astype(np.float32)


def _cymbal_sound(sample_rate: int, np: object, random: object) -> object:
    duration = 0.55
    time = np.arange(round(sample_rate * duration)) / sample_rate
    noise = random.standard_normal(time.size)
    bright_noise = noise - np.roll(noise, 1)
    return (bright_noise * np.exp(-time * 7) * 0.12).astype(np.float32)
