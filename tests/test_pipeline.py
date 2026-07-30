from pathlib import Path

from koshien_music_converter.pipeline import build_fluidsynth_command


def test_fluidsynth_options_precede_input_files() -> None:
    command = build_fluidsynth_command(
        "fluidsynth.exe",
        Path("brass.sf2"),
        Path("melody.mid"),
        Path("brass.wav"),
    )

    assert command == [
        "fluidsynth.exe",
        "-ni",
        "-F",
        "brass.wav",
        "-r",
        "44100",
        "brass.sf2",
        "melody.mid",
    ]
