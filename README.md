# bizeny_sinister

Unholy Desire Mix - Sinister Aesthetic v8 によるアニメ/イラスト画像生成API（RunPod Serverless）

## 概要

テキストプロンプトからアニメ・イラスト画像を生成するAPI。ComfyUIバックエンドでUnholy Desire Mix - Sinister Aesthetic v8モデル（Illustriousベース）を使用し、RunPod Serverless上で動作する。

## 機能

- テキストからアニメ/イラスト画像生成
- Danbooruタグ + 自然言語対応
- 自動品質タグ付与（masterpiece, best quality, absurdres）
- 複数LoRAスタック対応（最大10個、URL指定）
- JPEG出力（品質指定可能）

## API パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| `prompt` | string | (必須) | 生成プロンプト |
| `negative_prompt` | string | (auto) | ネガティブプロンプト |
| `width` | int | 1024 | 画像幅（8の倍数に自動調整） |
| `height` | int | 1024 | 画像高さ（8の倍数に自動調整） |
| `steps` | int | 20 | 推論ステップ数 |
| `seed` | int | 42 | ランダムシード |
| `cfg` | float | 2.5 | CFGスケール |
| `quality` | int | 90 | JPEG品質 (1-100) |
| `no_quality_tags` | bool | false | 品質タグ自動付与を無効化 |
| `loras` | array | (none) | LoRAオブジェクト配列 `{url, strength}`（最大10） |
| `lora_url` | string | (none) | レガシー: 単一LoRA URL（`loras`と併用不可） |
| `lora_strength` | float | 0.8 | レガシー: 単一LoRA強度 (-2.0〜2.0) |

## ビルド

```bash
docker build -t bizeny-sinister .
```

チェックポイントはイメージに含まれず、コンテナ起動時にダウンロードされる。
RunPodの環境変数に `CIVITAI_API_TOKEN` を設定すること。

## 構成

| コンポーネント | 詳細 |
|--------------|------|
| 生成モデル | Unholy Desire Mix - Sinister Aesthetic v8 (Illustriousベース, ~6.5GB) |
| CLIP Skip | 2 |
| サンプラー | DPM++ 2M (Karras) |
| CFG | 2.5 |
| バックエンド | ComfyUI |
| GPU | NVIDIA 8GB+ |
| 出力形式 | JPEG (Base64) |

## bizeny_imd との違い

| 項目 | bizeny_imd | bizeny_sinister |
|------|-----------|-----------------|
| モデル | Illustrious XL v2.0 | Unholy Desire Mix - Sinister Aesthetic v8 |
| サンプラー | Euler Ancestral / Normal | DPM++ 2M / Karras |
| CFG | 6.0 | 2.5 |
| Steps | 28 | 20 |
| モデルソース | HuggingFace (ungated) | Civitai |
