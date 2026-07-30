from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .config import ArrangementSettings
from .errors import ConversionError, DependencyError


@dataclass(frozen=True)
class TranscriptionStats:
    raw_note_count: int
    merged_note_count: int
    cleaned_note_count: int
    final_note_count: int
    average_note_duration: float
    minimum_note_duration: float
    maximum_note_duration: float
    phrase_count: int


@dataclass(frozen=True)
class SimplificationStats:
    raw_note_count: int
    merged_note_count: int
    cleaned_note_count: int
    quantized_note_count: int


def transcribe_melody(
    source: Path,
    destination: Path,
    settings: ArrangementSettings,
    bpm: float,
) -> TranscriptionStats:
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

        regions = extract_note_regions(
            frequencies, voiced, times, rms, minimum_duration=0.04
        )
        simplified_regions, simplification = process_note_regions(
            regions, bpm=bpm, settings=settings
        )
        articulated_regions = adjust_note_lengths(
            simplified_regions, bpm=bpm, settings=settings
        )
        final_regions, phrase_count = shape_note_phrases(
            articulated_regions, bpm=bpm, settings=settings
        )
        trumpet.control_changes.extend(
            [
                pretty_midi.ControlChange(
                    number=73, value=settings.brass_attack_controller, time=0
                ),
                pretty_midi.ControlChange(
                    number=72, value=settings.brass_release_controller, time=0
                ),
            ]
        )
        for pitch, start, end, level in final_regions:
            velocity = max(
                settings.minimum_brass_velocity,
                min(127, round(120 * level / reference_rms)),
            )
            trumpet.notes.append(
                pretty_midi.Note(
                    velocity=velocity, pitch=pitch, start=start, end=end
                )
            )
        if not trumpet.notes:
            raise ConversionError("主旋律として扱える音程を検出できませんでした。")
        midi.instruments.append(trumpet)
        midi.write(str(destination))
        durations = [end - start for _pitch, start, end, _level in final_regions]
        return TranscriptionStats(
            raw_note_count=len(regions),
            merged_note_count=simplification.merged_note_count,
            cleaned_note_count=simplification.cleaned_note_count,
            final_note_count=len(final_regions),
            average_note_duration=sum(durations) / len(durations),
            minimum_note_duration=min(durations),
            maximum_note_duration=max(durations),
            phrase_count=phrase_count,
        )
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"主旋律の採譜に失敗しました: {exc}") from exc


def normalize_midi_pitch(pitch: int, minimum: int, maximum: int) -> int:
    """音名を保ったまま、トランペット向け音域へオクターブ移動する。"""
    while pitch < minimum:
        pitch += 12
    while pitch > maximum:
        pitch -= 12
    return max(minimum, min(maximum, pitch))


def simplify_note_regions(
    regions: list[tuple[int, float, float, float]],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> list[tuple[int, float, float, float]]:
    simplified, _stats = process_note_regions(
        regions, bpm=bpm, settings=settings
    )
    return simplified


def process_note_regions(
    regions: list[tuple[int, float, float, float]],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> tuple[list[tuple[int, float, float, float]], SimplificationStats]:
    """揺れの多い採譜結果を応援ラッパ向けの単純なノート列へする。"""
    normalized = [
        (
            normalize_midi_pitch(
                pitch, settings.minimum_midi_note, settings.maximum_midi_note
            ),
            start,
            end,
            level,
        )
        for pitch, start, end, level in regions
    ]
    merged = merge_similar_notes(normalized, bpm=bpm, settings=settings)
    cleaned = remove_decorative_notes(merged, bpm=bpm, settings=settings)
    quantized = quantize_note_regions(cleaned, bpm=bpm, settings=settings)
    return quantized, SimplificationStats(
        raw_note_count=len(regions),
        merged_note_count=len(merged),
        cleaned_note_count=len(cleaned),
        quantized_note_count=len(quantized),
    )


def merge_similar_notes(
    notes: list[tuple[int, float, float, float]],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> list[tuple[int, float, float, float]]:
    """短い間隔で続く同音・近似音を、明確な連打を残しながら統合する。"""
    if not notes:
        return []
    maximum_gap = 60 / bpm * settings.same_note_merge_max_gap_beats
    maximum_duration = 60 / bpm * settings.maximum_merged_note_beats
    merged = [notes[0]]

    for pitch, start, end, level in notes[1:]:
        previous_pitch, previous_start, previous_end, previous_level = merged[-1]
        gap = start - previous_end
        combined_end = max(previous_end, end)
        if (
            abs(pitch - previous_pitch) <= settings.same_note_pitch_tolerance
            and gap <= maximum_gap
            and combined_end - previous_start <= maximum_duration
        ):
            merged[-1] = (
                previous_pitch,
                previous_start,
                combined_end,
                max(previous_level, level),
            )
        else:
            merged.append((pitch, start, end, level))
    return merged


def remove_decorative_notes(
    notes: list[tuple[int, float, float, float]],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> list[tuple[int, float, float, float]]:
    """短音を前後関係から吸収し、孤立した装飾音だけを削除する。"""
    working = list(notes)
    reduced: list[tuple[int, float, float, float]] = []
    index = 0
    ornament_limit = 60 / bpm * settings.ornament_max_duration_beats

    while index < len(working):
        current = working[index]
        following = working[index + 1] if index + 1 < len(working) else None
        previous = reduced[-1] if reduced else None
        duration = current[2] - current[1]
        returns_to_previous = (
            previous is not None
            and following is not None
            and abs(previous[0] - following[0])
            <= settings.same_note_pitch_tolerance
            and abs(previous[0] - current[0])
            > settings.same_note_pitch_tolerance
            and duration <= ornament_limit
        )

        if returns_to_previous:
            assert previous is not None and following is not None
            reduced[-1] = (
                previous[0],
                previous[1],
                following[2],
                max(previous[3], following[3]),
            )
            index += 2
            continue

        if duration < settings.minimum_note_duration:
            if (
                previous is not None
                and abs(previous[0] - current[0])
                <= settings.same_note_pitch_tolerance
            ):
                reduced[-1] = (
                    previous[0],
                    previous[1],
                    current[2],
                    max(previous[3], current[3]),
                )
            elif (
                following is not None
                and abs(following[0] - current[0])
                <= settings.same_note_pitch_tolerance
            ):
                working[index + 1] = (
                    following[0],
                    current[1],
                    following[2],
                    max(current[3], following[3]),
                )
            index += 1
            continue

        reduced.append(current)
        index += 1
    return reduced


def quantize_note_regions(
    notes: list[tuple[int, float, float, float]],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> list[tuple[int, float, float, float]]:
    """8分・4分音符を中心に、短いフレーズだけ16分音符を許可する。"""
    beat = 60 / bpm
    eighth = beat / settings.quantize_subdivision
    sixteenth = beat / 4
    duration_candidates = [eighth, beat, beat * 2, beat * 3]
    if settings.allow_sixteenth_notes:
        duration_candidates.insert(0, sixteenth)

    candidates: list[tuple[int, float, float, float]] = []
    for pitch, start, end, level in notes:
        source_duration = end - start
        use_sixteenth_grid = (
            settings.allow_sixteenth_notes and source_duration < eighth * 0.75
        )
        start_grid = sixteenth if use_sixteenth_grid else eighth
        quantized_start = round(start / start_grid) * start_grid
        quantized_duration = min(
            duration_candidates,
            key=lambda duration: (abs(duration - source_duration), -duration),
        )
        candidates.append(
            (
                pitch,
                quantized_start,
                quantized_start + quantized_duration,
                level,
            )
        )

    density_limited: list[tuple[int, float, float, float]] = []
    for note in candidates:
        recent_starts = [
            existing[1]
            for existing in density_limited
            if note[1] - beat < existing[1] <= note[1]
        ]
        if len(recent_starts) >= settings.maximum_notes_per_beat:
            continue
        density_limited.append(note)

    monophonic: list[tuple[int, float, float, float]] = []
    for note in density_limited:
        pitch, start, end, level = note
        if monophonic and start < monophonic[-1][2]:
            previous = monophonic[-1]
            if start <= previous[1]:
                if level > previous[3]:
                    monophonic[-1] = note
                continue
            monophonic[-1] = (
                previous[0], previous[1], start, previous[3]
            )
        monophonic.append((pitch, start, end, level))
    return monophonic


def adjust_note_lengths(
    regions: list[tuple[int, float, float, float]],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> list[tuple[int, float, float, float]]:
    """元音価を残しながら、Release前に小さな発音間隔を作る。"""
    maximum_duration = 60 / bpm * settings.maximum_note_beats
    adjusted: list[tuple[int, float, float, float]] = []
    for pitch, start, end, level in regions:
        source_duration = end - start
        played_duration = (
            min(source_duration, maximum_duration) * settings.note_shortening_ratio
        )
        played_duration = max(
            min(source_duration, settings.minimum_note_duration),
            played_duration,
        )
        adjusted.append((pitch, start, start + played_duration, level))
    return adjusted


def shape_note_phrases(
    notes: list[tuple[int, float, float, float]],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> tuple[list[tuple[int, float, float, float]], int]:
    """元の空白と音高跳躍から息継ぎ位置を作り、末尾音を少し伸ばす。"""
    if not notes:
        return [], 0
    beat = 60 / bpm
    boundary_gap = beat * settings.phrase_boundary_gap_beats
    minimum_rest = beat * settings.minimum_phrase_rest_beats
    maximum_phrase = beat * settings.maximum_phrase_beats
    maximum_note = beat * settings.maximum_note_beats
    shaped = list(notes)
    phrase_start_index = 0
    boundaries: list[int] = []

    for index in range(1, len(shaped)):
        previous = shaped[index - 1]
        current = shaped[index]
        gap = current[1] - previous[2]
        phrase_duration = current[1] - shaped[phrase_start_index][1]
        large_jump = (
            index - phrase_start_index >= 4
            and abs(current[0] - previous[0])
            >= settings.phrase_pitch_jump_semitones
        )
        if (
            gap >= boundary_gap
            or phrase_duration >= maximum_phrase
            or large_jump
        ):
            boundaries.append(index)
            phrase_start_index = index

    for boundary in boundaries:
        shaped[boundary - 1] = _extend_phrase_end(
            shaped[boundary - 1],
            settings=settings,
            maximum_note=maximum_note,
            next_start=shaped[boundary][1],
            minimum_rest=minimum_rest,
        )
    shaped[-1] = _extend_phrase_end(
        shaped[-1],
        settings=settings,
        maximum_note=maximum_note,
    )
    return shaped, len(boundaries) + 1


def _extend_phrase_end(
    note: tuple[int, float, float, float],
    *,
    settings: ArrangementSettings,
    maximum_note: float,
    next_start: float | None = None,
    minimum_rest: float = 0,
) -> tuple[int, float, float, float]:
    pitch, start, end, level = note
    duration = end - start
    desired_end = min(
        start + maximum_note,
        start + duration * settings.phrase_end_extension_ratio,
    )
    if next_start is not None:
        rest_ceiling = next_start - minimum_rest
        if rest_ceiling > start:
            desired_end = min(desired_end, rest_ceiling)
    return pitch, start, max(start + settings.minimum_note_duration, desired_end), level


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
