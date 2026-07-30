from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

from .errors import ConversionError, DependencyError

LogCallback = Callable[[str], None]


def require_command(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise DependencyError(
            f"{name} が見つかりません。READMEの手順に従ってインストールし、"
            "PATHを設定してください。"
        )
    return path


def run_command(
    command: Sequence[str],
    log: LogCallback,
    *,
    cwd: Path | None = None,
) -> None:
    display = " ".join(f'"{part}"' if " " in part else part for part in command)
    log(f"> {display}")
    try:
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError as exc:
        raise ConversionError(f"コマンドを開始できませんでした: {exc}") from exc

    assert process.stdout is not None
    for line in process.stdout:
        line = line.strip()
        if line:
            log(line)
    return_code = process.wait()
    if return_code != 0:
        raise ConversionError(
            f"外部コマンドが終了コード {return_code} で失敗しました。"
        )

