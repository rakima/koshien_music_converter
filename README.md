# koshien_music_converter

MP3の一部分を、トランペットと応援太鼓が目立つ「甲子園の応援団風」
アレンジへ変換するWindows向けネタツールです。すべてローカルで動作し、
外部APIやAPI課金はありません。

> [!NOTE]
> MVP版です。原曲やSoundFontによって結果は大きく変わります。
> 音楽としての忠実さより、短いデモを楽しめることを優先しています。

## 処理内容

1. ffmpegで指定区間（最大30秒）を切り抜く
2. Demucsでボーカル、その他、ドラム、ベースへ分離する
3. librosaでボーカル優先の主旋律候補をMIDI化する
4. 抽出直後のraw MIDIを保存する
5. 極短音、完全同音、開始位置だけを最小限に後処理する
6. 音高を変えず、必要な音だけオクターブ単位でラッパ音域へ移す
7. FluidSynthとSoundFontでMIDIをトランペット音にする
8. BPM同期の大太鼓・小太鼓4拍パターンを生成する
9. 生成ラッパと生成太鼓だけをミックスする
10. コンプレッサー、ラウドネス調整、リミッターで約-1 dBFSに整える

## 必要環境

- Windows 10/11
- Python 3.14（64 bit）
- ffmpeg（`ffmpeg`コマンドにPATHが通っていること）
- FluidSynth（`fluidsynth`コマンドにPATHが通っていること）
- General MIDI対応の `.sf2` SoundFont
- 初回のDemucsモデル取得用インターネット接続

AIライブラリはサイズが大きく、初回インストールと初回変換には時間が
かかります。変換後はモデルのキャッシュを使うため、通常はオフラインで
利用できます。GPUは必須ではありませんが、CPUでは数分かかる場合があります。

## セットアップ

PowerShellでリポジトリのルートを開き、仮想環境を作成します。

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

ffmpegとFluidSynthを別途インストールし、次のコマンドが成功することを
確認してください。

```powershell
ffmpeg -version
fluidsynth --version
```

SoundFontはライセンスを確認のうえ、General MIDI音源の `.sf2` ファイルを
用意してください。GUIから毎回指定できます。トランペットの音色は
General MIDIプログラム56を使用します。

## 起動

```powershell
python -m koshien_music_converter
```

または、インストール後に次のコマンドでも起動できます。

```powershell
koshien-music-converter
```

GUIで以下を指定して「変換開始」を押します。

- 入力MP3
- 出力MP3
- SoundFont（`.sf2`）
- 開始秒
- 終了秒（開始から最大30秒）

初回実行時はDemucsが学習済みモデルをダウンロードします。ログ欄に処理状況が
表示され、完了すると指定先へMP3が保存されます。

## 開発

開発用依存関係を追加してテストを実行します。

```powershell
pip install -e ".[dev]"
pytest
```

主な構成は以下のとおりです。

```text
src/koshien_music_converter/
  app.py       Tkinter GUIとバックグラウンド処理
  config.py    入力値と検証
  pipeline.py  音声変換の手順
  commands.py  外部コマンド実行とログ転送
  errors.py    利用者向け例外
tests/         外部AIモデルを使わない単体テスト
```

アレンジの既定値は`config.py`の`ArrangementSettings`へまとめています。
GUI項目を増やさずに、以下を一か所で調整できます。

- トランペットのMIDI音域: 60〜84
- ラッパ音量: 1.15
- 生成応援太鼓音量: 1.10
- raw抽出時の最小ノート長: 0.08秒（初期版と同値）
- 後処理で削除する極短音: 0.03秒未満
- 開始位置の量子化単位: 16分音符（最大移動0.04秒）
- 完全同音の統合間隔: 0.03秒
- 近似音統合、音密度制限、音高平滑化、フレーズ整形: 無効
- MIDIノートの一律短縮: 無効
- デバッグ成果物の保存: 有効
- ラッパAttack/Release: 各20
- ラッパ中域・高域補正: +4 dB / +3 dB
- 太鼓低域補正: +5 dB
- シンバル間隔: 4小節
- 目標ラウドネス: -14 LUFS
- 最終ピーク: -1 dBFS

原曲ステムは旋律とBPMの解析にのみ使い、完成MP3には混ぜません。
変換ログにはraw/後処理後それぞれのノート数、音域、音価、削除・統合・
オクターブ移動数に加え、太鼓イベント数、ミックス音量、完成MP3の最大ピークが
表示されます。

開発中は、出力先の `debug/<出力ファイル名>/` に以下を保存します。

```text
vocal_or_melody_source.wav
melody_raw.mid
melody_processed.mid
output_raw_melody.wav
output_processed_melody.wav
trumpet_only.wav
drums_only.wav
final_mix.wav
```

`output_raw_melody.wav` と `output_processed_melody.wav` は太鼓を含まないため、
抽出時点と後処理後の旋律を同じラッパ音色で比較できます。保存は
`ArrangementSettings.save_debug_artifacts` で無効化できます。

## 既知の制約

- 主旋律抽出はボーカルを優先しつつ目立つ楽器も薄く参照する簡易方式です。
- 無料SoundFontの音色品質によって「甲子園っぽさ」が変わります。
- Demucsの初回モデル取得中はオフラインで実行できません。
- 変換処理のキャンセルと設定保存は未実装です。
- 入力はMP3、出力はMP3、変換区間は最大30秒に限定しています。

## ライセンス

[MIT License](LICENSE)
