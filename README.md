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
4. 同音統合、前後関係による装飾音除去、音密度制限を行う
5. 8分・4分中心の緩やかな量子化とフレーズ処理を行う
6. 元音価を88%残し、Releaseの短い明瞭な奏法へ変換する
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
- 最小ノート長: 0.10秒
- 量子化単位: 8分音符
- 16分音符: 短いフレーズのみ許可
- 1拍あたりの最大ノート数: 2
- 同音判定の音高差: 1半音
- 同音統合の最大間隔: 0.35拍
- 統合後の最大ノート長: 3拍
- ノート短縮率: 0.88
- 最大ノート長: 3拍
- フレーズ末尾延長率: 1.30
- フレーズ間の最小休符: 0.35拍
- ラッパAttack/Release: 各20
- ラッパ中域・高域補正: +4 dB / +3 dB
- 太鼓低域補正: +5 dB
- シンバル間隔: 4小節
- 目標ラウドネス: -14 LUFS
- 最終ピーク: -1 dBFS

原曲ステムは旋律とBPMの解析にのみ使い、完成MP3には混ぜません。
変換ログには推定BPM、太鼓イベント数、MIDIノート数、平均・最大ノート長、
同時発音数、各パートのミックス音量、完成MP3の最大ピークが表示されます。

## 既知の制約

- 主旋律抽出はボーカルを優先しつつ目立つ楽器も薄く参照する簡易方式です。
- 無料SoundFontの音色品質によって「甲子園っぽさ」が変わります。
- Demucsの初回モデル取得中はオフラインで実行できません。
- 変換処理のキャンセルと設定保存は未実装です。
- 入力はMP3、出力はMP3、変換区間は最大30秒に限定しています。

## ライセンス

[MIT License](LICENSE)
