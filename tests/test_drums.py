from pathlib import Path

import soundfile as sf

from koshien_music_converter.drums import build_cheer_pattern, generate_cheer_drums


def test_cheer_pattern_uses_stable_four_beat_rhythm() -> None:
    events = build_cheer_pattern(duration=2, bpm=120)

    assert events
    assert {event.kind for event in events} == {
        "odaiko",
        "odaiko_accent",
        "snare",
        "cymbal",
    }
    assert [(event.time, event.kind) for event in events] == [
        (0.0, "odaiko_accent"),
        (0.5, "snare"),
        (1.0, "odaiko"),
        (1.5, "snare"),
        (0.0, "cymbal"),
    ]


def test_cymbal_is_added_every_four_bars() -> None:
    events = build_cheer_pattern(duration=10, bpm=120, cymbal_interval_bars=4)

    assert [event.time for event in events if event.kind == "cymbal"] == [0, 8]


def test_generated_cheer_drums_are_not_silent(tmp_path: Path) -> None:
    destination = tmp_path / "cheer.wav"

    event_count = generate_cheer_drums(destination, duration=2, bpm=120)
    audio, sample_rate = sf.read(destination)

    assert event_count > 0
    assert sample_rate == 44100
    assert audio.max() > 0.5
