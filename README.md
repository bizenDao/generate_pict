# generate_pict

AutismMix Pony によるアニメ/イラスト画像生成API（RunPod Serverless）

## 概要

テキストプロンプトからアニメ・イラスト画像を生成するAPI。ComfyUIバックエンドでAutismMix Pony（SDXLベース）モデルを使用し、RunPod Serverless上で動作する。

## 機能

- テキストからアニメ/イラスト画像生成
- Ponyベースの高品質SDXL生成
- 自動品質タグ付与（score_9, score_8_up, score_7_up, source_anime）
- JPEG出力（品質指定可能）

## API パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `prompt` | string | (必須) | 生成プロンプト |
| `negative_prompt` | string | (auto) | ネガティブプロンプト |
| `width` | int | 1024 | 画像幅（8の倍数に自動調整） |
| `height` | int | 1024 | 画像高さ（8の倍数に自動調整） |
| `steps` | int | 25 | 推論ステップ数 |
| `seed` | int | 42 | ランダムシード |
| `cfg` | float | 7.0 | CFGスケール |
| `quality` | int | 90 | JPEG品質 (1-100) |
| `no_quality_tags` | bool | false | 品質タグ自動付与を無効化 |

## ビルド

```bash
docker build -t generate-pict .
```

## 構成

| コンポーネント | 詳細 |
|--------------|------|
| 生成モデル | AutismMix Pony (SDXL, ~7.2GB, public/ungated) |
| CLIP Skip | 2 |
| サンプラー | DPM++ 2M Karras |
| バックエンド | ComfyUI |
| GPU | NVIDIA 8GB+ |
| 出力形式 | JPEG (Base64) |
