from __future__ import annotations

import math
from pathlib import Path

from .errors import ConversionError, DependencyError


def transcribe_melody(source: Path, destination: Path) -> None:
    """音声の最も強いピッチ軌跡をトランペットMIDIへ変換する。"""
    try:
        import librosa
        import numpy as np
        import pretty_midi
    except ImportError as exc:
        raise DependencyError(
            "主旋律抽出ライブラリを読み込めません。pip install -e . を実行してください。"
        ) from exc

    try:
        audio, sample_rate = librosa.load(source, sr=22050, mono=True)
        frame_length = 2048
        hop_length = 256
        frequencies, voiced, _probabilities = librosa.pyin(
            audio,
            fmin=librosa.note_to_hz("C2"),
            fmax=librosa.note_to_hz("C7"),
            sr=sample_rate,
            frame_length=frame_length,
            hop_length=hop_length,
        )
        times = librosa.times_like(
            frequencies, sr=sample_rate, hop_length=hop_length
        )
        rms = librosa.feature.rms(
            y=audio, frame_length=frame_length, hop_length=hop_length
        )[0]
        midi = pretty_midi.PrettyMIDI()
        trumpet = pretty_midi.Instrument(program=56, name="Trumpet")
        valid_rms = rms[rms > 0]
        reference_rms = float(np.percentile(valid_rms, 90)) if valid_rms.size else 1.0

        for pitch, start, end, level in extract_note_regions(
            frequencies, voiced, times, rms
        ):
            velocity = max(55, min(120, round(105 * level / reference_rms)))
            trumpet.notes.append(
                pretty_midi.Note(
                    velocity=velocity, pitch=pitch, start=start, end=end
                )
            )
        if not trumpet.notes:
            raise ConversionError("主旋律として扱える音程を検出できませんでした。")
        midi.instruments.append(trumpet)
        midi.write(str(destination))
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"主旋律の採譜に失敗しました: {exc}") from exc


def extract_note_regions(
    frequencies: object,
    voiced: object,
    times: object,
    levels: object,
    *,
    minimum_duration: float = 0.08,
) -> list[tuple[int, float, float, float]]:
    """フレーム単位のピッチを連続したMIDIノートへまとめる。"""
    notes: list[tuple[int, float, float, float]] = []
    current_pitch: int | None = None
    start = 0.0
    last_time = 0.0
    collected_levels: list[float] = []

    def finish(end: float) -> None:
        nonlocal current_pitch, collected_levels
        if (
            current_pitch is not None
            and end - start >= minimum_duration
            and collected_levels
        ):
            notes.append(
                (current_pitch, start, end, sum(collected_levels) / len(collected_levels))
            )
        current_pitch = None
        collected_levels = []

    for frequency, is_voiced, time, level in zip(
        frequencies, voiced, times, levels, strict=False
    ):
        frame_time = float(time)
        pitch = (
            round(69 + 12 * math.log2(float(frequency) / 440))
            if bool(is_voiced) and math.isfinite(float(frequency))
            else None
        )
        if pitch != current_pitch:
            finish(frame_time)
            if pitch is not None:
                current_pitch = max(0, min(127, pitch))
                start = frame_time
        if current_pitch is not None:
            collected_levels.append(float(level))
        last_time = frame_time

    frame_duration = max(0.01, last_time - start) if current_pitch is not None else 0
    finish(last_time + frame_duration)
    return notes
