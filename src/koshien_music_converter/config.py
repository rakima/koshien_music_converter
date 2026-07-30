from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConversionError


@dataclass(frozen=True)
class ArrangementSettings:
    """甲子園応援風アレンジの調整値。"""

    minimum_midi_note: int = 60
    maximum_midi_note: int = 84
    brass_volume: float = 1.15
    generated_drum_volume: float = 1.1
    original_drum_volume: float = 0.25
    accompaniment_volume: float = 0.20
    vocal_volume: float = 0.05
    minimum_note_duration: float = 0.12
    quantize_subdivision: int = 2
    target_loudness_lufs: float = -14.0
    target_peak_dbfs: float = -1.0
    loudness_range: float = 9.0
    compressor_threshold_db: float = -18.0
    compressor_ratio: float = 3.0
    compressor_attack_ms: float = 10.0
    compressor_release_ms: float = 120.0

    def validate(self) -> None:
        if not 0 <= self.minimum_midi_note <= self.maximum_midi_note <= 127:
            raise ConversionError("MIDI音域設定は0〜127の範囲で指定してください。")
        if self.minimum_note_duration <= 0:
            raise ConversionError("最小ノート長は0より大きくしてください。")
        if self.quantize_subdivision not in (2, 4):
            raise ConversionError("量子化単位は8分音符（2）または16分音符（4）です。")
        if self.target_peak_dbfs > 0:
            raise ConversionError("出力ピークは0 dBFS以下にしてください。")
        for name, value in (
            ("ラッパ音量", self.brass_volume),
            ("生成太鼓音量", self.generated_drum_volume),
            ("原曲ドラム音量", self.original_drum_volume),
            ("伴奏音量", self.accompaniment_volume),
            ("ボーカル音量", self.vocal_volume),
        ):
            if value < 0:
                raise ConversionError(f"{name}は0以上にしてください。")


@dataclass(frozen=True)
class ConversionConfig:
    input_path: Path
    output_path: Path
    start_seconds: float
    end_seconds: float
    soundfont_path: Path
    arrangement: ArrangementSettings = field(default_factory=ArrangementSettings)

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds

    def validate(self) -> None:
        self.arrangement.validate()
        if not self.input_path.is_file():
            raise ConversionError("入力MP3ファイルが見つかりません。")
        if self.input_path.suffix.lower() != ".mp3":
            raise ConversionError("入力にはMP3ファイルを指定してください。")
        if self.start_seconds < 0:
            raise ConversionError("開始秒は0以上にしてください。")
        if self.end_seconds <= self.start_seconds:
            raise ConversionError("終了秒は開始秒より後にしてください。")
        if self.duration > 30:
            raise ConversionError("MVPでは変換区間を30秒以内にしてください。")
        if not self.output_path.parent.is_dir():
            raise ConversionError("出力先フォルダーが見つかりません。")
        if self.output_path.suffix.lower() != ".mp3":
            raise ConversionError("出力ファイルの拡張子は.mp3にしてください。")
        if not self.soundfont_path.is_file():
            raise ConversionError(
                "SoundFontが見つかりません。設定から.sf2ファイルを指定してください。"
            )

