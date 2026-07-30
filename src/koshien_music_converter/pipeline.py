from __future__ import annotations

import sys
import tempfile
from collections.abc import Callable
from pathlib import Path

from .commands import require_command, run_command
from .config import ConversionConfig
from .drums import estimate_bpm, generate_cheer_drums
from .errors import ConversionError
from .melody import transcribe_melody
from .mixing import build_mix_filter

ProgressCallback = Callable[[int, str], None]


def build_fluidsynth_command(
    executable: str,
    soundfont: Path,
    midi: Path,
    output: Path,
) -> list[str]:
    """Windows版でも解釈されるよう、オプションを入力ファイルより前へ置く。"""
    return [
        executable,
        "-ni",
        "-F",
        str(output),
        "-r",
        "44100",
        str(soundfont),
        str(midi),
    ]


class ConversionPipeline:
    def __init__(self, progress: ProgressCallback | None = None) -> None:
        self._progress = progress or (lambda _value, _message: None)

    def convert(self, config: ConversionConfig) -> None:
        config.validate()
        ffmpeg = require_command("ffmpeg")
        fluidsynth = require_command("fluidsynth")

        with tempfile.TemporaryDirectory(prefix="koshien_converter_") as temp:
            work = Path(temp)
            clip = work / "clip.wav"
            self._notify(5, "指定区間を切り抜いています")
            run_command(
                [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                    "-ss", str(config.start_seconds),
                    "-t", str(config.duration),
                    "-i", str(config.input_path),
                    "-ar", "44100", "-ac", "2", str(clip),
                ],
                self._log,
            )

            self._notify(15, "AIで楽器を分離しています（初回はモデルを取得します）")
            run_command(
                [
                    sys.executable, "-m", "demucs", "--name", "htdemucs",
                    "--out", str(work / "separated"), str(clip),
                ],
                self._log,
            )
            stems = work / "separated" / "htdemucs" / clip.stem
            self._require_stems(stems)
            bpm = estimate_bpm(stems / "drums.wav")
            self._log(f"解析テンポ: {bpm:.1f} BPM")

            melody_source = work / "melody_source.wav"
            self._notify(52, "主旋律用の音声を作っています")
            run_command(
                [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                    "-i", str(stems / "vocals.wav"), "-i", str(stems / "other.wav"),
                    "-filter_complex",
                    "[0:a]volume=1.2[v];[1:a]volume=0.15[o];"
                    "[v][o]amix=inputs=2:normalize=0,alimiter=limit=0.95",
                    str(melody_source),
                ],
                self._log,
            )

            midi_path = work / "melody.mid"
            self._notify(60, "主旋律を採譜しています")
            transcription = transcribe_melody(
                melody_source, midi_path, config.arrangement, bpm
            )
            self._log(
                "MIDIノート数: "
                f"抽出={transcription.raw_note_count}, "
                f"補正後={transcription.final_note_count}; "
                "音域="
                f"{config.arrangement.minimum_midi_note}"
                f"〜{config.arrangement.maximum_midi_note}"
            )
            brass = work / "brass.wav"
            self._notify(72, "主旋律をトランペット音へ変換しています")
            run_command(
                build_fluidsynth_command(
                    fluidsynth, config.soundfont_path, midi_path, brass
                ),
                self._log,
            )
            if not brass.is_file():
                raise ConversionError(
                    "FluidSynthは正常終了しましたが、ブラス音声を生成できませんでした。"
                )

            original_taiko = work / "original_taiko.wav"
            self._notify(82, "ドラムを応援太鼓風に加工しています")
            run_command(
                [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                    "-i", str(stems / "drums.wav"),
                    "-af",
                    "highpass=f=45,lowpass=f=4800,"
                    "bass=g=10:f=110:w=0.7,"
                    "acompressor=threshold=-20dB:ratio=5:attack=3:release=100,"
                    "volume=1.35,alimiter=limit=0.95",
                    str(original_taiko),
                ],
                self._log,
            )

            cheer_drums = work / "cheer_drums.wav"
            drum_events = generate_cheer_drums(
                cheer_drums, config.duration, bpm
            )
            self._log(f"応援太鼓: BPM={bpm:.1f}, イベント数={drum_events}")

            self._notify(90, "ブラスと応援太鼓をミックスしています")
            mix_filter = build_mix_filter(config.arrangement)
            self._log(
                "ミックス音量: "
                f"ラッパ={config.arrangement.brass_volume:.2f}, "
                f"生成太鼓={config.arrangement.generated_drum_volume:.2f}, "
                f"原曲ドラム={config.arrangement.original_drum_volume:.2f}, "
                f"伴奏={config.arrangement.accompaniment_volume:.2f}, "
                f"ボーカル={config.arrangement.vocal_volume:.2f}; "
                f"目標={config.arrangement.target_loudness_lufs:.1f} LUFS, "
                f"ピーク={config.arrangement.target_peak_dbfs:.1f} dBFS"
            )
            run_command(
                [
                    ffmpeg, "-y", "-hide_banner", "-loglevel", "warning",
                    "-i", str(brass), "-i", str(cheer_drums),
                    "-i", str(original_taiko), "-i", str(stems / "other.wav"),
                    "-i", str(stems / "bass.wav"),
                    "-i", str(stems / "vocals.wav"),
                    "-filter_complex", mix_filter,
                    "-map", "[out]", "-t", str(config.duration),
                    "-codec:a", "libmp3lame", "-q:a", "2",
                    str(config.output_path),
                ],
                self._log,
            )
        self._notify(100, f"完了: {config.output_path}")

    def _require_stems(self, stems: Path) -> None:
        missing = [
            name for name in ("vocals.wav", "other.wav", "drums.wav", "bass.wav")
            if not (stems / name).is_file()
        ]
        if missing:
            raise ConversionError(
                "ステム分離結果が不足しています: " + ", ".join(missing)
            )

    def _notify(self, value: int, message: str) -> None:
        self._progress(value, message)

    def _log(self, message: str) -> None:
        self._progress(-1, message)
