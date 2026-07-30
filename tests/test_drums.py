from pathlib import Path

import soundfile as sf

from koshien_music_converter.drums import build_cheer_pattern, generate_cheer_drums


def test_cheer_pattern_uses_don_don_dodon_don_rhythm() -> None:
    events = build_cheer_pattern(duration=2, bpm=120)

    assert events
    assert {event.kind for event in events} == {
        "odaiko",
        "odaiko_accent",
        "cymbal",
    }
    assert [
        event.time for event in events if event.kind.startswith("odaiko")
    ] == [0, 0.5, 1.0, 1.25, 1.5]


def test_generated_cheer_drums_are_not_silent(tmp_path: Path) -> None:
    destination = tmp_path / "cheer.wav"

    event_count = generate_cheer_drums(destination, duration=2, bpm=120)
    audio, sample_rate = sf.read(destination)

    assert event_count > 0
    assert sample_rate == 44100
    assert audio.max() > 0.5
