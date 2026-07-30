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
3. librosaでボーカルと楽器から主旋律候補をMIDI化する
4. FluidSynthとSoundFontでMIDIをトランペット音にする
5. ドラムを低域強調・圧縮して応援太鼓風にする
6. ブラス、太鼓、薄く残したベースをミックスしてMP3にする

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

## 既知の制約

- 主旋律抽出はボーカルや目立つ楽器を拾う簡易方式です。
- 無料SoundFontの音色品質によって「甲子園っぽさ」が変わります。
- Demucsの初回モデル取得中はオフラインで実行できません。
- 変換処理のキャンセルと設定保存は未実装です。
- 入力はMP3、出力はMP3、変換区間は最大30秒に限定しています。

## ライセンス

[MIT License](LICENSE)
