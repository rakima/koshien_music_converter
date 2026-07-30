from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .errors import ConversionError


@dataclass(frozen=True)
class ConversionConfig:
    input_path: Path
    output_path: Path
    start_seconds: float
    end_seconds: float
    soundfont_path: Path

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds

    def validate(self) -> None:
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

