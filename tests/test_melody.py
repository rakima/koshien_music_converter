import pytest

from koshien_music_converter.config import ArrangementSettings
from koshien_music_converter.melody import (
    calculate_melody_stats,
    extract_note_regions,
    merge_exact_same_notes,
    normalize_midi_pitch,
    process_note_regions,
    quantize_note_starts,
    remove_extremely_short_notes,
)


def test_extract_note_regions_matches_initial_grouping() -> None:
    notes = extract_note_regions(
        [440.0, 440.0, 440.0, float("nan"), 523.25, 523.25, 523.25],
        [True, True, True, False, True, True, True],
        [0.00, 0.04, 0.08, 0.12, 0.16, 0.20, 0.24],
        [0.5, 0.6, 0.7, 0.0, 0.8, 0.9, 1.0],
    )

    assert notes[0] == pytest.approx((69, 0.0, 0.12, 0.6))
    assert notes[1] == pytest.approx((72, 0.16, 0.32, 0.9))


def test_extract_note_regions_uses_configurable_raw_threshold() -> None:
    notes = extract_note_regions(
        [440.0, float("nan")],
        [True, False],
        [0.0, 0.04],
        [1.0, 0.0],
        minimum_duration=0.03,
    )

    assert len(notes) == 1


@pytest.mark.parametrize(
    ("source", "expected"),
    [(48, 60), (59, 71), (60, 60), (84, 84), (85, 73), (96, 84)],
)
def test_normalize_midi_pitch_only_moves_octaves(source: int, expected: int) -> None:
    assert normalize_midi_pitch(source, minimum=60, maximum=84) == expected
    assert (expected - source) % 12 == 0


def test_remove_extremely_short_notes_does_not_absorb_pitch() -> None:
    notes = [(72, 0.0, 0.02, 0.5), (73, 0.02, 0.08, 0.8)]

    assert remove_extremely_short_notes(notes, 0.03) == [notes[1]]


def test_merge_exact_same_notes_does_not_merge_near_pitch() -> None:
    notes = [
        (72, 0.0, 0.2, 0.5),
        (73, 0.21, 0.4, 0.8),
        (73, 0.41, 0.6, 0.7),
    ]

    assert merge_exact_same_notes(notes, 0.03) == [
        notes[0],
        (73, 0.21, 0.6, 0.8),
    ]


def test_quantization_changes_only_start_and_preserves_duration() -> None:
    notes = [(72, 0.13, 0.43, 0.8), (74, 0.51, 0.91, 0.9)]

    quantized = quantize_note_starts(
        notes, bpm=120, subdivision=4, maximum_shift=0.04
    )

    assert [note[0] for note in quantized] == [72, 74]
    assert quantized[0][1] == pytest.approx(0.125)
    assert quantized[1][1] == pytest.approx(0.5)
    assert quantized[0][2] - quantized[0][1] == pytest.approx(0.3)
    assert quantized[1][2] - quantized[1][1] == pytest.approx(0.4)


def test_quantization_leaves_start_when_grid_is_too_far() -> None:
    quantized = quantize_note_starts(
        [(72, 0.18, 0.5, 1.0)],
        bpm=120,
        subdivision=4,
        maximum_shift=0.01,
    )

    assert quantized[0][1] == pytest.approx(0.18)


def test_default_processing_preserves_pitch_sequence_except_octaves() -> None:
    source = [
        (48, 0.0, 0.2, 0.6),
        (61, 0.21, 0.4, 0.7),
        (62, 0.41, 0.6, 0.8),
    ]

    processed, stats = process_note_regions(
        source, bpm=120, settings=ArrangementSettings()
    )

    assert [note[0] for note in processed] == [60, 61, 62]
    assert stats.pitch_changed_note_count == 0
    assert stats.octave_shifted_note_count == 1
    assert stats.removed_note_count == 0
    assert stats.merged_note_count == 0


def test_each_minimal_processing_step_can_be_disabled() -> None:
    settings = ArrangementSettings(
        enable_short_note_removal=False,
        enable_exact_note_merge=False,
        enable_start_quantization=False,
        minimum_midi_note=0,
        maximum_midi_note=127,
    )
    source = [(72, 0.013, 0.02, 0.5), (72, 0.021, 0.08, 0.7)]

    processed, stats = process_note_regions(source, bpm=120, settings=settings)

    assert processed == source
    assert stats.removed_note_count == 0
    assert stats.merged_note_count == 0


def test_melody_statistics_include_range_duration_and_density() -> None:
    stats = calculate_melody_stats(
        [(60, 0.0, 0.25, 0.5), (72, 0.5, 1.0, 0.8)]
    )

    assert stats.note_count == 2
    assert stats.minimum_pitch == 60
    assert stats.maximum_pitch == 72
    assert stats.pitch_range == 12
    assert stats.average_note_duration == pytest.approx(0.375)
    assert stats.notes_per_second == pytest.approx(2.0)
