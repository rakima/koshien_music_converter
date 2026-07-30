from __future__ import annotations

import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import cast

from .config import ConversionConfig
from .errors import ConversionError
from .pipeline import ConversionPipeline


class ConverterApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("甲子園ミュージックコンバーター")
        self.root.geometry("720x540")
        self.root.minsize(620, 480)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()

        self.input_var = tk.StringVar()
        self.output_var = tk.StringVar()
        self.start_var = tk.StringVar(value="0")
        self.end_var = tk.StringVar(value="15")
        self.soundfont_var = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="MP3とSoundFontを選択してください")

        self._build()
        self.root.after(100, self._drain_events)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill=tk.BOTH, expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)

        self._path_row(frame, 0, "入力MP3", self.input_var, self._select_input)
        self._path_row(frame, 1, "出力MP3", self.output_var, self._select_output)
        self._path_row(
            frame, 2, "SoundFont", self.soundfont_var, self._select_soundfont
        )

        ttk.Label(frame, text="開始秒").grid(row=3, column=0, sticky=tk.W, pady=6)
        ttk.Entry(frame, textvariable=self.start_var, width=12).grid(
            row=3, column=1, sticky=tk.W, pady=6
        )
        ttk.Label(frame, text="終了秒").grid(row=4, column=0, sticky=tk.W, pady=6)
        ttk.Entry(frame, textvariable=self.end_var, width=12).grid(
            row=4, column=1, sticky=tk.W, pady=6
        )

        self.convert_button = ttk.Button(
            frame, text="変換開始", command=self._start_conversion
        )
        self.convert_button.grid(row=5, column=0, columnspan=3, pady=(12, 8))
        ttk.Progressbar(
            frame, variable=self.progress_var, maximum=100
        ).grid(row=6, column=0, columnspan=3, sticky=tk.EW)

        log_frame = ttk.LabelFrame(frame, text="ログ", padding=6)
        log_frame.grid(row=7, column=0, columnspan=3, sticky=tk.NSEW, pady=(12, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log = tk.Text(log_frame, height=12, wrap=tk.WORD, state=tk.DISABLED)
        self.log.grid(row=0, column=0, sticky=tk.NSEW)
        scrollbar = ttk.Scrollbar(log_frame, command=self.log.yview)
        scrollbar.grid(row=0, column=1, sticky=tk.NS)
        self.log.configure(yscrollcommand=scrollbar.set)
        ttk.Label(frame, textvariable=self.status_var).grid(
            row=8, column=0, columnspan=3, sticky=tk.W, pady=(6, 0)
        )

    def _path_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        command: object,
    ) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=6)
        ttk.Entry(parent, textvariable=variable).grid(
            row=row, column=1, sticky=tk.EW, padx=8, pady=6
        )
        ttk.Button(parent, text="参照", command=command).grid(row=row, column=2)

    def _select_input(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("MP3", "*.mp3")])
        if path:
            self.input_var.set(path)
            if not self.output_var.get():
                source = Path(path)
                self.output_var.set(str(source.with_name(source.stem + "_koshien.mp3")))

    def _select_output(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".mp3", filetypes=[("MP3", "*.mp3")]
        )
        if path:
            self.output_var.set(path)

    def _select_soundfont(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("SoundFont", "*.sf2")])
        if path:
            self.soundfont_var.set(path)

    def _start_conversion(self) -> None:
        try:
            config = ConversionConfig(
                input_path=Path(self.input_var.get()),
                output_path=Path(self.output_var.get()),
                start_seconds=float(self.start_var.get()),
                end_seconds=float(self.end_var.get()),
                soundfont_path=Path(self.soundfont_var.get()),
            )
            config.validate()
        except ValueError:
            messagebox.showerror("入力エラー", "開始秒と終了秒は数値で入力してください。")
            return
        except ConversionError as exc:
            messagebox.showerror("入力エラー", str(exc))
            return

        self.convert_button.configure(state=tk.DISABLED)
        self.progress_var.set(0)
        self._append_log("変換を開始します")
        threading.Thread(
            target=self._convert_worker, args=(config,), daemon=True
        ).start()

    def _convert_worker(self, config: ConversionConfig) -> None:
        try:
            ConversionPipeline(self._publish_progress).convert(config)
        except Exception as exc:
            self.events.put(("error", str(exc)))
        else:
            self.events.put(("done", str(config.output_path)))

    def _publish_progress(self, value: int, message: str) -> None:
        self.events.put(("progress", (value, message)))

    def _drain_events(self) -> None:
        try:
            while True:
                event, payload = self.events.get_nowait()
                if event == "progress":
                    value, message = cast(tuple[int, str], payload)
                    if value >= 0:
                        self.progress_var.set(value)
                        self.status_var.set(message)
                    self._append_log(message)
                elif event == "error":
                    self.convert_button.configure(state=tk.NORMAL)
                    self.status_var.set("変換に失敗しました")
                    self._append_log(f"エラー: {payload}")
                    messagebox.showerror("変換エラー", str(payload))
                elif event == "done":
                    self.convert_button.configure(state=tk.NORMAL)
                    self.status_var.set("変換が完了しました")
                    messagebox.showinfo("完了", f"出力しました:\n{payload}")
        except queue.Empty:
            pass
        self.root.after(100, self._drain_events)

    def _append_log(self, message: object) -> None:
        self.log.configure(state=tk.NORMAL)
        self.log.insert(tk.END, str(message) + "\n")
        self.log.see(tk.END)
        self.log.configure(state=tk.DISABLED)


def main() -> None:
    root = tk.Tk()
    ConverterApp(root)
    root.mainloop()
