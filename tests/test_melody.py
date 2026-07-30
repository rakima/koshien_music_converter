import pytest

from koshien_music_converter.config import ArrangementSettings
from koshien_music_converter.melody import (
    adjust_note_lengths,
    extract_note_regions,
    merge_similar_notes,
    normalize_midi_pitch,
    remove_decorative_notes,
    simplify_note_regions,
)


def test_extract_note_regions_groups_equal_pitch() -> None:
    notes = extract_note_regions(
        [440.0, 440.0, 440.0, float("nan"), 523.25, 523.25, 523.25],
        [True, True, True, False, True, True, True],
        [0.00, 0.04, 0.08, 0.12, 0.16, 0.20, 0.24],
        [0.5, 0.6, 0.7, 0.0, 0.8, 0.9, 1.0],
    )

    assert len(notes) == 2
    assert notes[0] == pytest.approx((69, 0.0, 0.12, 0.6))
    assert notes[1] == pytest.approx((72, 0.16, 0.32, 0.9))


def test_extract_note_regions_discards_short_notes() -> None:
    notes = extract_note_regions(
        [440.0, float("nan")],
        [True, False],
        [0.0, 0.04],
        [1.0, 0.0],
    )

    assert notes == []


@pytest.mark.parametrize(
    ("source", "expected"),
    [(48, 60), (59, 71), (60, 60), (84, 84), (85, 73), (96, 84)],
)
def test_normalize_midi_pitch_uses_trumpet_range(
    source: int, expected: int
) -> None:
    assert normalize_midi_pitch(source, minimum=60, maximum=84) == expected


def test_simplify_notes_removes_short_notes_and_merges_pitch_wobble() -> None:
    regions = [
        (71, 0.01, 0.20, 0.5),
        (72, 0.21, 0.38, 0.7),
        (67, 0.39, 0.44, 0.8),
        (64, 0.51, 0.78, 0.6),
    ]

    simplified = simplify_note_regions(
        regions, bpm=120, settings=ArrangementSettings()
    )

    assert simplified == [
        (71, 0.0, 0.25, 0.7),
        (64, 0.5, 0.75, 0.6),
    ]
    assert len(simplified) < len(regions)


def test_simplified_notes_use_eighth_note_grid() -> None:
    settings = ArrangementSettings(quantize_subdivision=2)
    simplified = simplify_note_regions(
        [(72, 0.13, 0.51, 1.0)], bpm=120, settings=settings
    )

    _pitch, start, end, _level = simplified[0]
    assert start == pytest.approx(0.25)
    assert end - start == pytest.approx(0.5)


def test_adjust_note_lengths_preserves_melody_and_caps_long_notes() -> None:
    settings = ArrangementSettings(
        note_shortening_ratio=0.9,
        maximum_note_beats=2,
        minimum_note_duration=0.1,
    )

    adjusted = adjust_note_lengths(
        [(72, 0.0, 2.0, 1.0), (74, 2.0, 2.25, 0.8)],
        bpm=120,
        settings=settings,
    )

    assert adjusted[0][2] == pytest.approx(0.9)
    assert adjusted[1][2] == pytest.approx(2.225)
    assert adjusted[0][2] < adjusted[1][1]


def test_remove_short_returning_ornament() -> None:
    notes = [
        (72, 0.0, 0.25, 0.8),
        (76, 0.25, 0.5, 0.5),
        (72, 0.5, 0.75, 0.9),
        (79, 0.75, 1.0, 0.7),
    ]

    reduced = remove_decorative_notes(
        notes,
        bpm=120,
        settings=ArrangementSettings(ornament_max_duration_beats=0.5),
    )

    assert reduced == [
        (72, 0.0, 0.75, 0.9),
        (79, 0.75, 1.0, 0.7),
    ]


def test_short_note_is_absorbed_into_close_following_note() -> None:
    reduced = remove_decorative_notes(
        [
            (72, 0.0, 0.08, 0.4),
            (73, 0.08, 0.4, 0.8),
            (79, 0.5, 0.8, 0.7),
        ],
        bpm=120,
        settings=ArrangementSettings(
            minimum_note_duration=0.1,
            same_note_pitch_tolerance=1,
        ),
    )

    assert reduced == [
        (73, 0.0, 0.4, 0.8),
        (79, 0.5, 0.8, 0.7),
    ]


def test_simplified_notes_are_monophonic() -> None:
    simplified = simplify_note_regions(
        [
            (72, 0.0, 0.6, 0.8),
            (76, 0.4, 0.8, 0.7),
            (79, 0.7, 1.0, 0.9),
        ],
        bpm=120,
        settings=ArrangementSettings(),
    )

    assert all(
        current[2] <= following[1]
        for current, following in zip(simplified, simplified[1:], strict=False)
    )


def test_merge_similar_notes_keeps_deliberate_repetition() -> None:
    settings = ArrangementSettings(
        same_note_pitch_tolerance=1,
        same_note_merge_max_gap_beats=0.25,
        maximum_merged_note_beats=2,
    )
    notes = [
        (72, 0.0, 0.2, 0.6),
        (73, 0.22, 0.4, 0.8),
        (72, 0.7, 0.9, 0.7),
    ]

    merged = merge_similar_notes(notes, bpm=120, settings=settings)

    assert merged == [
        (72, 0.0, 0.4, 0.8),
        (72, 0.7, 0.9, 0.7),
    ]
