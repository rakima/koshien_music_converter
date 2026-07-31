from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConversionError


@dataclass(frozen=True)
class ArrangementSettings:
    """変換処理で現在使用している調整値。"""

    # MIDI抽出・後処理
    minimum_midi_note: int = 60
    maximum_midi_note: int = 84
    raw_minimum_note_duration: float = 0.08
    extreme_short_note_duration: float = 0.03
    quantize_subdivision: int = 4
    maximum_quantize_shift_seconds: float = 0.04
    exact_note_merge_max_gap_seconds: float = 0.03
    enable_short_note_removal: bool = True
    enable_exact_note_merge: bool = True
    enable_start_quantization: bool = True

    # ラッパ音源
    brass_attack_controller: int = 20
    brass_release_controller: int = 20
    minimum_brass_velocity: int = 96
    brass_volume: float = 1.15
    brass_presence_db: float = 4.0
    brass_brightness_db: float = 3.0

    # 応援太鼓
    generated_drum_volume: float = 1.1
    drum_body_db: float = 5.0
    cymbal_interval_bars: int = 4

    # 最終ミックス
    target_loudness_lufs: float = -14.0
    target_peak_dbfs: float = -1.0
    loudness_range: float = 9.0
    compressor_threshold_db: float = -18.0
    compressor_ratio: float = 3.0
    compressor_attack_ms: float = 10.0
    compressor_release_ms: float = 120.0

    # 中間成果物
    save_debug_artifacts: bool = True

    def validate(self) -> None:
        if not 0 <= self.minimum_midi_note <= self.maximum_midi_note <= 127:
            raise ConversionError("MIDI音域設定は0〜127の範囲で指定してください。")
        if self.raw_minimum_note_duration < 0:
            raise ConversionError("抽出時の最小ノート長は0以上にしてください。")
        if self.extreme_short_note_duration < 0:
            raise ConversionError("極短音の削除基準は0以上にしてください。")
        if self.quantize_subdivision not in (2, 4):
            raise ConversionError("量子化単位は8分音符（2）または16分音符（4）です。")
        if self.maximum_quantize_shift_seconds < 0:
            raise ConversionError("量子化の最大移動秒数は0以上にしてください。")
        if self.exact_note_merge_max_gap_seconds < 0:
            raise ConversionError("完全同音の統合間隔は0以上にしてください。")
        for controller in (
            self.brass_attack_controller,
            self.brass_release_controller,
            self.minimum_brass_velocity,
        ):
            if not 0 <= controller <= 127:
                raise ConversionError("MIDIコントローラー値は0〜127にしてください。")
        for name, value in (
            ("ラッパ中域補正", self.brass_presence_db),
            ("ラッパ高域補正", self.brass_brightness_db),
            ("太鼓低域補正", self.drum_body_db),
        ):
            if not -12 <= value <= 12:
                raise ConversionError(f"{name}は-12〜12 dBで指定してください。")
        if self.cymbal_interval_bars <= 0:
            raise ConversionError("シンバル間隔は1小節以上にしてください。")
        if self.target_peak_dbfs > 0:
            raise ConversionError("出力ピークは0 dBFS以下にしてください。")
        for name, value in (
            ("ラッパ音量", self.brass_volume),
            ("生成太鼓音量", self.generated_drum_volume),
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

