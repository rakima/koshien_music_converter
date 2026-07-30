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
    minimum_note_duration: float = 0.10
    quantize_subdivision: int = 2
    allow_sixteenth_notes: bool = True
    maximum_notes_per_beat: int = 2
    same_note_pitch_tolerance: int = 1
    same_note_merge_max_gap_beats: float = 0.35
    maximum_merged_note_beats: float = 3.0
    ornament_max_duration_beats: float = 0.5
    note_shortening_ratio: float = 0.88
    maximum_note_beats: float = 3.0
    phrase_end_extension_ratio: float = 1.30
    minimum_phrase_rest_beats: float = 0.35
    phrase_boundary_gap_beats: float = 0.75
    phrase_pitch_jump_semitones: int = 7
    maximum_phrase_beats: float = 8.0
    brass_attack_controller: int = 20
    brass_release_controller: int = 20
    minimum_brass_velocity: int = 96
    brass_presence_db: float = 4.0
    brass_brightness_db: float = 3.0
    drum_body_db: float = 5.0
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
        if self.maximum_notes_per_beat <= 0:
            raise ConversionError("1拍あたりの最大ノート数は1以上にしてください。")
        if not 0 <= self.same_note_pitch_tolerance <= 12:
            raise ConversionError("同音判定の音高差は0〜12にしてください。")
        if self.same_note_merge_max_gap_beats < 0:
            raise ConversionError("同音統合の最大間隔は0以上にしてください。")
        if self.maximum_merged_note_beats <= 0:
            raise ConversionError("統合後の最大ノート長は0より大きくしてください。")
        if self.ornament_max_duration_beats <= 0:
            raise ConversionError("装飾音の最大拍数は0より大きくしてください。")
        if not 0 < self.note_shortening_ratio <= 1:
            raise ConversionError("ノート短縮率は0より大きく1以下にしてください。")
        if self.maximum_note_beats <= 0:
            raise ConversionError("最大ノート拍数は0より大きくしてください。")
        if self.phrase_end_extension_ratio < 1:
            raise ConversionError("フレーズ末尾の延長率は1以上にしてください。")
        if self.minimum_phrase_rest_beats < 0:
            raise ConversionError("フレーズ間の最小休符は0以上にしてください。")
        if self.phrase_boundary_gap_beats <= 0:
            raise ConversionError("フレーズ境界の空白は0より大きくしてください。")
        if not 1 <= self.phrase_pitch_jump_semitones <= 24:
            raise ConversionError("フレーズ境界の音高差は1〜24にしてください。")
        if self.maximum_phrase_beats <= 0:
            raise ConversionError("最大フレーズ拍数は0より大きくしてください。")
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

