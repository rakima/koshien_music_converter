class ConversionError(RuntimeError):
    """利用者に表示できる変換エラー。"""


class DependencyError(ConversionError):
    """外部ツールやライブラリが不足している場合のエラー。"""

