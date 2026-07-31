# koshien_music_converter

**Status: Experimental / Development Suspended**

MP3の指定区間から主旋律候補を抽出し、ラッパと応援太鼓だけで
「甲子園の応援団風」の音源を生成するWindows向けGUIツールです。

短期間で遊べるネタツールの完成を目指し、ステム分離、ピッチ抽出、MIDI化、
SoundFontによる演奏、太鼓生成までをローカル処理で組み合わせた技術検証です。
外部APIやAPI課金は使用せず、原曲の音声は完成音源へ混ぜません。

## 現在のステータス

本プロジェクトは実験段階です。

MP3から主旋律を自動抽出し、甲子園応援風に変換することを目的としていましたが、
現時点では主旋律抽出の精度が十分ではなく、期待する品質には到達していません。
ネタツールとして想定していた開発規模を超えるため、現在は開発を停止しています。

コードは技術検証の記録として残しています。楽曲によっては旋律として認識できる
結果になりますが、安定した変換品質を保証する完成品ではありません。

## 実装済み機能

- Tkinter GUIからのMP3、出力先、SoundFont、開始秒、終了秒の指定
- ffmpegによる最大30秒の切り抜き
- Demucs `htdemucs` によるボーカル、その他、ドラム、ベースのステム分離
- ボーカルを優先した主旋律候補音声の作成
- `librosa.pyin` による単音ピッチ抽出とMIDI変換
- 極端な短音、完全な同音、開始位置に限定した軽いMIDI後処理
- ラッパ音域から外れた音のオクターブ補正
- FluidSynthとGeneral MIDI SoundFontによるトランペット音のレンダリング
- 推定BPMに同期した大太鼓、小太鼓、シンバルの生成
- 生成したラッパと太鼓のみのミックス
- コンプレッサー、ラウドネス調整、リミッターによる音量調整
- ログと進捗表示
- raw/processed MIDI、比較用ラッパ音源、各パート、最終WAVの保存

YouTube等から音源を取得する機能、動画出力、MIDI編集機能はありません。

## 処理の流れ

```text
MP3の指定区間
  ↓
Demucsでステム分離
  ↓
ボーカル＋その他ステムから主旋律候補を作成
  ↓
pyinでピッチ抽出 → raw MIDI
  ↓
最小限の後処理 → processed MIDI
  ↓
FluidSynthでラッパ音を生成
  ＋
BPM同期の応援太鼓を生成
  ↓
ミックス、音量調整、MP3出力
```

## 判明した課題

- 楽曲によって主旋律抽出精度が大きく変わる
- ボーカルの細かいピッチ変化や装飾音を過剰に拾う場合がある
- MIDI後処理を強くすると必要なメロディまで失われる
- MIDI後処理を弱くすると演奏が細かくなりすぎる
- ラッパ音源へ置換するだけでは甲子園応援らしさが不足する
- 適切な量子化やノート整理の設定が楽曲ごとに異なる
- 複数音や伴奏が強い区間では、単音ピッチ抽出が主旋律以外を追うことがある
- 完全自動で安定した変換結果を得ることが難しい

現在の実装は、強い後処理で旋律を失うことを避けるため、抽出した音高推移を
優先して残す設定です。そのため、細かな誤検出が残る場合があります。

## 実行環境

最後に確認した構成は以下です。

- Windows 10/11
- Python 3.14（64 bit）
- ffmpeg（PATH上で `ffmpeg` を実行可能）
- FluidSynth 2.5系（PATH上で `fluidsynth` を実行可能）
- General MIDI対応の `.sf2` SoundFont
- Demucsモデル初回取得用のインターネット接続

Pythonの対応範囲は `pyproject.toml` で `>=3.14,<3.15` に限定しています。
他のOSやPythonバージョンでは、このリポジトリの状態では動作確認していません。
Demucsは初回変換時に学習済みモデルを取得します。取得後は通常キャッシュが
利用されますが、キャッシュの場所は利用環境やライブラリの設定に依存します。

## セットアップ

PowerShellでリポジトリのルートを開き、仮想環境を作成します。

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .
```

`requirements.txt` を使う場合も、同じ実行用依存がインストールされます。

```powershell
pip install -r requirements.txt
```

ffmpeg、FluidSynth、SoundFontはPythonパッケージには含まれません。別途用意し、
以下を確認してください。

```powershell
ffmpeg -version
fluidsynth --version
```

SoundFontはライセンスを確認したうえで、General MIDI対応の `.sf2` を用意します。
トランペットにはGeneral MIDIプログラム56を使用します。

## 起動と基本操作

仮想環境を有効にして起動します。

```powershell
python -m koshien_music_converter
```

または、編集可能インストール後は次のコマンドでも起動できます。

```powershell
koshien-music-converter
```

GUIで次の項目を指定し、「変換開始」を押します。

1. 権利上利用可能な入力MP3
2. 出力するMP3のパス
3. SoundFont（`.sf2`）
4. 開始秒
5. 終了秒（開始から最大30秒）

完成MP3は指定した出力先へ保存されます。開発用の中間成果物は、既定では
出力先と同じフォルダーの `debug/<出力ファイル名>/` に保存されます。

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

`output_raw_melody.wav` と `output_processed_melody.wav` は太鼓を含まず、抽出直後と
後処理後の旋律を比較するためのものです。保存は
`ArrangementSettings.save_debug_artifacts` で無効化できます。

## 設定

現行処理で使用する値は `config.py` の `ArrangementSettings` にまとめています。

- MIDI抽出・後処理: 抽出時の最小音価、極短音の基準、開始位置の量子化、
  完全同音の統合間隔、ラッパ音域
- ラッパ音源: Attack、Release、最低Velocity、音量、中高域補正
- 太鼓生成: 音量、低域補正、シンバル間隔
- ミックス: 目標LUFS、ピーク、コンプレッサー、リミッター
- デバッグ: 中間成果物の保存有無

GUIからこれらの詳細値を変更する機能は実装していません。

## 開発と確認

開発用依存を追加してテストします。

```powershell
pip install -e ".[dev]"
pytest
```

主なモジュールは以下です。

```text
src/koshien_music_converter/
  app.py       GUIとバックグラウンド実行
  config.py    入出力・変換設定と検証
  pipeline.py  ステム分離から出力までの処理順
  melody.py    ピッチ抽出、MIDI生成、最小後処理
  drums.py     BPM解析と応援太鼓生成
  mixing.py    ミックスと音量調整用ffmpegフィルター
  commands.py  外部コマンド実行とログ転送
  errors.py    利用者向け例外
tests/         外部AIモデルを実行しない単体テスト
```

## 将来再開する場合の検討候補

以下は現在のTODOではなく、別の方針で技術検証を再開する場合の候補です。

- 別の主旋律抽出モデルとの比較
- ボーカル専用ピッチ抽出の改善
- 複数モデルの抽出結果比較
- raw MIDIを手動修正できる簡易エディタ
- 楽曲特性ごとのプリセット
- ラッパ音源と太鼓音源の改善
- 抽出処理を省略できるMIDIファイル入力

再開時は、まず `debug` 内のraw/processed MIDIと比較音源を確認し、問題が
ステム分離、ピッチ抽出、MIDI後処理、音色のどこで生じているかを切り分けるのが
適切です。

## 音源と著作権に関する注意

- ユーザー自身が権利を持つ音源、または利用許可を得た音源を使用してください。
- 本ツールは、著作権で保護された音源の取得や配布を目的としていません。
- YouTube等から音源をダウンロードする機能は提供していません。
- 生成音源を利用・公開する場合も、元音源やSoundFontの権利条件を確認してください。

これは一般的な注意事項です。個別の音源の利用可否を判断するものではありません。
このリポジトリには、検証に使用した市販楽曲や変換後音源を含めていません。

## 開発停止について

現在は開発を停止しています。

より高精度な主旋律抽出手法が利用可能になった場合や、別の実装方針が
見つかった場合に再開する可能性があります。

## ライセンス

[MIT License](LICENSE)
