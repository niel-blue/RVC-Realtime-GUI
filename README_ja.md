# RVC-Realtime-GUI

[English](README.md) | [日本語](README_ja.md)

> ## 最新の高速リアルタイム推論ビルド
>
> **本プロジェクトには、2026-07-18 以降に導入されたリアルタイム推論の高速化対応を取り込んでいます。**
> 更新済みの推論経路、CUDA Graph のウォームアップ、入出力ノイズ低減の修正を、低遅延 RVC 音声変換向けの専用デスクトップクライアントとしてまとめています。

<img width="1760" height="752" alt="RVC-Realtime-GUI screenshot" src="https://github.com/user-attachments/assets/d001d48b-9f00-4eeb-a90c-1474099e8454" />

RVC-Realtime-GUI は、低遅延のリアルタイム RVC（Retrieval-based Voice Conversion）を行う Windows デスクトップクライアントです。

本リポジトリには **CUDA 12.8 標準ビルド**のソースコードを収録しています。
[RVC-Project/Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) をベースに、リアルタイム推論に特化して改修しています。

## 高速化対応

- **更新済みリアルタイム推論実装**：2026-07-18 以降の本家更新を反映
- **CUDA Graph ウォームアップ**：起動後の継続的な GPU 推論オーバーヘッドを削減
- **入出力ノイズ低減の修正**：更新済みリアルタイム経路の不具合修正を反映
- **CUDA 12.8 標準ランタイム**：Blackwell 互換環境を含む現行 NVIDIA GPU に対応

## ダウンロード

**[Hugging Face のダウンロードページを開く](https://huggingface.co/niel-blue/RVC-Realtime-GUI)**

使用する NVIDIA GPU に合ったパッケージをダウンロードしてください。

- **CUDA 12.8**：現行の標準ビルド
- **CUDA 11.8**：CUDA 12.8 パッケージを使用できない旧世代 NVIDIA GPU 向け（準備中）

配布パッケージには、Python ランタイム、PyTorch／CUDA スタック、FFmpeg、推論用アセット、リリース用モデルセットを同梱しています。

## ビルド一覧

| ビルド | 状態 | 想定するハードウェア |
| --- | --- | --- |
| CUDA 12.8 | 現行標準ビルド | Blackwell 互換環境を含む現行 NVIDIA GPU |
| CUDA 11.8 | 準備中のレガシービルド | CUDA 12.8 パッケージを使用できない旧世代 NVIDIA GPU |

各ビルドは Python、PyTorch、CUDA ランタイムを自己完結させるため、Hugging Face 上で別々の配布パッケージとして提供します。

## 主な機能

- 日本語・英語対応の CustomTkinter 専用デスクトップ UI
- CUDA 12.8 標準ビルドと現行 NVIDIA GPU 対応
- CUDA Graph ウォームアップを備えたリアルタイム RVC 推論
- WASAPI およびネイティブ ASIO のオーディオデバイスルーティング
- 入力・出力・モニター用デバイスの個別選択
- モデルギャラリーとモデルごとの一般設定保存
- WAV 録音：入力／出力の別ファイル、ミックス、L/R 分離録音
- 同梱 FFmpeg を使った音声ファイル入力
- ランタイムログの表示・ファイル保存

## ソース構成

| パス | 用途 |
| --- | --- |
| `app/` | アプリケーションの起動処理と GUI |
| `infer/` | RVC リアルタイム推論、HuBERT、RMVPE、FCPE コード |
| `tools/` | GUI アダプタ、オーディオルーティング、録音、ファイル入力、補助機能 |
| `configs/config.py` | CUDA デバイスと精度設定 |
| `models/README.md` | 配布アプリが使用するモデルフォルダ構成 |
| `tests/` | ソースレベルの回帰テスト |

## Git に含めないもの

Git リポジトリには、ユーザー固有の設定や大容量バイナリを意図的に含めていません。

- 同梱 Python ランタイム、PyTorch、CUDA ライブラリ、パッケージキャッシュ
- RVC の `.pth` モデルおよび FAISS `.index` ファイル
- HuBERT、RMVPE の重みファイル
- FFmpeg バイナリ
- 録音データ、ログ、ウィンドウ位置、ローカルデバイス設定

これらはソース履歴ではなく、Hugging Face の配布パッケージに含めるものです。

## 開発

このソースツリーは、配布版 CUDA 12.8 ビルドの開発用です。配布パッケージを基準ランタイムとして使用し、次の起動ファイルを実行します。

```bat
RVC-Realtime-GUI-CUDA128.bat
```

パッケージには `runtime/`、`assets/`、`tools/ffmpeg/`、および `models/` 以下に少なくとも1つのモデルフォルダが必要です。

## 本家・ライセンス

本プロジェクトは RVC-Project による RVC-WebUI をベースにしています。帰属とライセンスについては [NOTICE.md](NOTICE.md)、[LICENSE](LICENSE)、および[ソースリポジトリ](https://github.com/niel-blue/RVC-Realtime-GUI)を参照してください。
