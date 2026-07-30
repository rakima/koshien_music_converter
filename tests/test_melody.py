import pytest

from koshien_music_converter.melody import extract_note_regions


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
