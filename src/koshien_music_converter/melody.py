from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .config import ArrangementSettings
from .errors import ConversionError, DependencyError

NoteRegion = tuple[int, float, float, float]


@dataclass(frozen=True)
class MelodyStats:
    note_count: int
    minimum_pitch: int
    maximum_pitch: int
    average_note_duration: float
    minimum_note_duration: float
    maximum_note_duration: float
    notes_per_second: float

    @property
    def pitch_range(self) -> int:
        return self.maximum_pitch - self.minimum_pitch


@dataclass(frozen=True)
class ProcessingStats:
    removed_note_count: int
    merged_note_count: int
    pitch_changed_note_count: int
    octave_shifted_note_count: int


@dataclass(frozen=True)
class TranscriptionResult:
    raw: MelodyStats
    processed: MelodyStats
    processing: ProcessingStats


def transcribe_melody(
    source: Path,
    raw_destination: Path,
    processed_destination: Path,
    settings: ArrangementSettings,
    bpm: float,
) -> TranscriptionResult:
    """初期版相当のpyin抽出結果と、最小後処理後のMIDIを保存する。"""
    try:
        import librosa
        import numpy as np
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
        valid_rms = rms[rms > 0]
        reference_rms = float(np.percentile(valid_rms, 90)) if valid_rms.size else 1.0
        raw_notes = extract_note_regions(
            frequencies,
            voiced,
            times,
            rms,
            minimum_duration=settings.raw_minimum_note_duration,
        )
        if not raw_notes:
            raise ConversionError("主旋律として扱える音程を検出できませんでした。")
        write_trumpet_midi(raw_notes, raw_destination, settings, reference_rms)
        processed_notes, processing = process_note_regions(
            raw_notes, bpm=bpm, settings=settings
        )
        write_trumpet_midi(
            processed_notes, processed_destination, settings, reference_rms
        )
        return TranscriptionResult(
            raw=calculate_melody_stats(raw_notes),
            processed=calculate_melody_stats(processed_notes),
            processing=processing,
        )
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"主旋律の採譜に失敗しました: {exc}") from exc


def write_trumpet_midi(
    notes: list[NoteRegion],
    destination: Path,
    settings: ArrangementSettings,
    reference_rms: float,
) -> None:
    try:
        import pretty_midi
    except ImportError as exc:
        raise DependencyError("pretty-midiを読み込めません。") from exc
    midi = pretty_midi.PrettyMIDI()
    trumpet = pretty_midi.Instrument(program=56, name="Trumpet")
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
    for pitch, start, end, level in notes:
        velocity = max(
            settings.minimum_brass_velocity,
            min(127, round(120 * level / max(reference_rms, 1e-9))),
        )
        trumpet.notes.append(
            pretty_midi.Note(velocity=velocity, pitch=pitch, start=start, end=end)
        )
    midi.instruments.append(trumpet)
    midi.write(str(destination))


def process_note_regions(
    regions: list[NoteRegion],
    *,
    bpm: float,
    settings: ArrangementSettings,
) -> tuple[list[NoteRegion], ProcessingStats]:
    """音高推移を保ち、個別に有効化された安全な処理だけを適用する。"""
    notes = list(regions)
    removed = 0
    merged = 0
    if settings.enable_short_note_removal:
        before = len(notes)
        notes = remove_extremely_short_notes(
            notes, settings.extreme_short_note_duration
        )
        removed = before - len(notes)
    if settings.enable_exact_note_merge:
        before = len(notes)
        notes = merge_exact_same_notes(
            notes, settings.exact_note_merge_max_gap_seconds
        )
        merged = before - len(notes)
    if settings.enable_start_quantization:
        notes = quantize_note_starts(
            notes,
            bpm=bpm,
            subdivision=settings.quantize_subdivision,
            maximum_shift=settings.maximum_quantize_shift_seconds,
        )
    shifted: list[NoteRegion] = []
    octave_shifted = 0
    for pitch, start, end, level in notes:
        normalized = normalize_midi_pitch(
            pitch, settings.minimum_midi_note, settings.maximum_midi_note
        )
        octave_shifted += normalized != pitch
        shifted.append((normalized, start, end, level))
    return shifted, ProcessingStats(
        removed_note_count=removed,
        merged_note_count=merged,
        pitch_changed_note_count=0,
        octave_shifted_note_count=octave_shifted,
    )


def remove_extremely_short_notes(
    notes: list[NoteRegion], minimum_duration: float
) -> list[NoteRegion]:
    return [note for note in notes if note[2] - note[1] >= minimum_duration]


def merge_exact_same_notes(
    notes: list[NoteRegion], maximum_gap: float
) -> list[NoteRegion]:
    """完全な同音で、重複またはごく短い空白だけを統合する。"""
    if not notes:
        return []
    merged = [notes[0]]
    for pitch, start, end, level in notes[1:]:
        previous_pitch, previous_start, previous_end, previous_level = merged[-1]
        gap = start - previous_end
        if pitch == previous_pitch and gap <= maximum_gap:
            merged[-1] = (
                previous_pitch,
                previous_start,
                max(previous_end, end),
                max(previous_level, level),
            )
        else:
            merged.append((pitch, start, end, level))
    return merged


def quantize_note_starts(
    notes: list[NoteRegion],
    *,
    bpm: float,
    subdivision: int,
    maximum_shift: float,
) -> list[NoteRegion]:
    """開始位置だけを軽く丸め、音価・音高・順序は維持する。"""
    grid = 60 / bpm / subdivision
    quantized: list[NoteRegion] = []
    previous_start = -math.inf
    for pitch, start, end, level in notes:
        candidate = round(start / grid) * grid
        new_start = candidate if abs(candidate - start) <= maximum_shift else start
        new_start = max(previous_start, new_start)
        duration = end - start
        quantized.append((pitch, new_start, new_start + duration, level))
        previous_start = new_start
    return quantized


def normalize_midi_pitch(pitch: int, minimum: int, maximum: int) -> int:
    """音名を変えず、トランペット音域へオクターブ単位で移動する。"""
    while pitch < minimum:
        pitch += 12
    while pitch > maximum:
        pitch -= 12
    return pitch


def calculate_melody_stats(notes: list[NoteRegion]) -> MelodyStats:
    if not notes:
        return MelodyStats(0, 0, 0, 0, 0, 0, 0)
    durations = [end - start for _pitch, start, end, _level in notes]
    elapsed = max(end for _pitch, _start, end, _level in notes) - min(
        start for _pitch, start, _end, _level in notes
    )
    pitches = [pitch for pitch, _start, _end, _level in notes]
    return MelodyStats(
        note_count=len(notes),
        minimum_pitch=min(pitches),
        maximum_pitch=max(pitches),
        average_note_duration=sum(durations) / len(durations),
        minimum_note_duration=min(durations),
        maximum_note_duration=max(durations),
        notes_per_second=len(notes) / elapsed if elapsed > 0 else 0,
    )


def extract_note_regions(
    frequencies: object,
    voiced: object,
    times: object,
    levels: object,
    *,
    minimum_duration: float = 0.08,
) -> list[NoteRegion]:
    """初期版と同じ方法で、pyinのピッチ軌跡をMIDIノートへまとめる。"""
    notes: list[NoteRegion] = []
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
