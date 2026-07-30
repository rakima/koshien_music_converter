from pathlib import Path

import soundfile as sf

from koshien_music_converter.drums import build_cheer_pattern, generate_cheer_drums


def test_cheer_pattern_contains_kicks_claps_and_cymbal() -> None:
    events = build_cheer_pattern(duration=2, bpm=120)

    assert events
    assert {event.kind for event in events} == {"kick", "clap", "cymbal"}
    assert [event.time for event in events if event.kind == "kick"] == [0, 1, 1.75]


def test_generated_cheer_drums_are_not_silent(tmp_path: Path) -> None:
    destination = tmp_path / "cheer.wav"

    event_count = generate_cheer_drums(destination, duration=2, bpm=120)
    audio, sample_rate = sf.read(destination)

    assert event_count > 0
    assert sample_rate == 44100
    assert audio.max() > 0.5
