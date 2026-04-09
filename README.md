# generate_pict

Nova 3DCG XL Illustrious v3.0 による3DCG/アニメ画像生成API（RunPod Serverless）

## 概要

テキストプロンプトから3DCGスタイルのアニメ・イラスト画像を生成するAPI。ComfyUIバックエンドでNova 3DCG XL Illustrious v3.0モデルを使用し、RunPod Serverless上で動作する。

## 機能

- テキストから3DCG/アニメ画像生成
- Danbooruタグ + 自然言語対応
- 自動品質タグ付与（masterpiece, best quality, absurdres）
- LoRA対応（URL指定でスタイル差し替え可能）
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
| `cfg` | float | 4.0 | CFGスケール |
| `quality` | int | 90 | JPEG品質 (1-100) |
| `no_quality_tags` | bool | false | 品質タグ自動付与を無効化 |
| `lora_url` | string | null | LoRAファイルURL (.safetensors) |
| `lora_strength` | float | 0.8 | LoRA適用強度 (-2.0〜2.0) |

## ビルド

```bash
docker build -t generate-pict .
```

## 構成

| コンポーネント | 詳細 |
|--------------|------|
| 生成モデル | Nova 3DCG XL Illustrious v3.0 (SDXL, ~6.5GB, public) |
| CLIP Skip | 2 |
| サンプラー | Euler Ancestral (Normal) |
| バックエンド | ComfyUI |
| GPU | NVIDIA 8GB+ |
| 出力形式 | JPEG (Base64) |
