# API 仕様書

## エンドポイント

### ジョブ送信

```
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/run
```

### ステータス確認

```
GET https://api.runpod.ai/v2/{ENDPOINT_ID}/status/{JOB_ID}
```

### 同期実行（短時間ジョブ向け）

```
POST https://api.runpod.ai/v2/{ENDPOINT_ID}/runsync
```

## 認証

```
Authorization: Bearer {RUNPOD_API_KEY}
```

## リクエスト

```json
{
  "input": {
    "prompt": "string (required)",
    "negative_prompt": "string (optional)",
    "width": 1024,
    "height": 1024,
    "steps": 28,
    "seed": 42,
    "cfg": 6.0,
    "quality": 90,
    "no_quality_tags": false,
    "loras": [
      {"url": "https://example.com/lora1.safetensors", "strength": 0.8},
      {"url": "https://example.com/lora2.safetensors", "strength": 0.5}
    ]
  }
}
```

## パラメータ詳細

### prompt (必須)

生成する画像の説明テキスト。Danbooruタグ形式または自然言語。

```
"1girl, long hair, blue eyes, school uniform, standing, outdoors"
```

`no_quality_tags` が false（デフォルト）の場合、自動的に以下が末尾に付与される:
```
masterpiece, best quality, absurdres
```

### negative_prompt

除外したい要素の指定。未指定時はデフォルト値が使用される。

デフォルト値:
```
worst quality, low quality, normal quality, lowres, bad anatomy,
bad hands, error, missing fingers, extra digit, fewer digits,
cropped, jpeg artifacts, signature, watermark, username, blurry
```

### width / height

| 制約 | 値 |
|------|-----|
| 最小値 | 64 |
| 最大値 | 2048 |
| 倍数制約 | 8の倍数に自動丸め |
| デフォルト | 1024 |

推奨解像度:

| アスペクト比 | 解像度 |
|-------------|--------|
| 1:1 | 1024 x 1024 |
| 3:4 (ポートレート) | 768 x 1024 |
| 4:3 (ランドスケープ) | 1024 x 768 |
| 9:16 (縦長) | 576 x 1024 |
| 16:9 (横長) | 1024 x 576 |

### steps

推論ステップ数。多いほど高品質だが生成時間が増加。

| 値 | 説明 |
|----|------|
| デフォルト | 28 |
| 推奨範囲 | 20-35 |
| 最小 | 1 |
| 最大 | 100 |

### cfg

Classifier-Free Guidance スケール。高いほどプロンプトに忠実。

| 値 | 説明 |
|----|------|
| デフォルト | 6.0 |
| 推奨範囲 | 4.0-8.0 |

### seed

乱数シード。同じseed + 同じパラメータで再現可能な結果を得られる。

| 値 | 説明 |
|----|------|
| 42 (デフォルト) | 固定シード |
| -1 | ランダム（毎回異なる結果） |
| 任意の整数 | 再現用 |

### quality

JPEG出力品質。

| 値 | ファイルサイズ | 画質 |
|----|-------------|------|
| 70 | 小 | やや劣化 |
| 85 | 中 | 良好 |
| 90 (デフォルト) | やや大 | 高品質 |
| 95 | 大 | 最高品質 |
| 100 | 最大 | 無劣化 |

### no_quality_tags

`true` にすると品質タグ（masterpiece 等）の自動付与を無効化する。独自のタグ体系を使いたい場合に利用。

### loras（複数LoRA対応）

LoRAを配列で指定する。最大10個まで。チェーン順にLoraLoaderノードが接続される。

```json
"loras": [
  {"url": "https://example.com/style.safetensors", "strength": 0.8},
  {"url": "https://example.com/character.safetensors", "strength": 0.6}
]
```

| フィールド | 型 | 必須 | 説明 |
|-----------|-----|------|------|
| `url` | string | はい | LoRAファイルのURL。`http(s)://`始まり、`.safetensors`終わり |
| `strength` | float | いいえ | 適用強度（model/clip共通）。デフォルトは`lora.json`の`default_strength`(0.8)。範囲: -2.0〜2.0 |

- `strength=0` のエントリは自動スキップ
- 未指定時は `lora.json` のデフォルトLoRAが使用される
- LoRAなし（デフォルトも未設定）の場合はCheckpointをそのまま使用

#### レガシー互換（単一LoRA）

従来の `lora_url` + `lora_strength` パラメータも引き続き使用可能。内部的に1要素の `loras` 配列に変換される。

| パラメータ | 型 | 説明 |
|-----------|-----|------|
| `lora_url` | string | LoRAファイルのURL |
| `lora_strength` | float | 適用強度 |

**注意**: `loras` と `lora_url` の同時指定はエラーになる。

## レスポンス

### 送信レスポンス

```json
{
  "id": "job-uuid-here",
  "status": "IN_QUEUE"
}
```

### ステータスレスポンス

#### 成功

```json
{
  "id": "job-uuid-here",
  "status": "COMPLETED",
  "output": {
    "image": "data:image/jpeg;base64,/9j/4AAQ...",
    "loras": [
      {
        "used": true,
        "source": "user",
        "url": "https://example.com/style.safetensors",
        "strength": 0.8,
        "size_mb": 8.38
      }
    ]
  }
}
```

#### 処理中

```json
{
  "id": "job-uuid-here",
  "status": "IN_PROGRESS"
}
```

#### 失敗

```json
{
  "id": "job-uuid-here",
  "status": "FAILED",
  "output": {
    "error": "error description"
  }
}
```

### ステータス一覧

| ステータス | 説明 |
|-----------|------|
| `IN_QUEUE` | キューで待機中 |
| `IN_PROGRESS` | 生成処理中 |
| `COMPLETED` | 完了（output にデータあり） |
| `FAILED` | 失敗（output.error に詳細） |
| `CANCELLED` | キャンセル済み |

## エラーレスポンス

| エラー | 原因 |
|--------|------|
| `prompt is required` | prompt パラメータ未指定 |
| `width must be between 64 and 2048` | 解像度が範囲外 |
| `steps must be between 1 and 100` | ステップ数が範囲外 |
| `quality must be between 1 and 100` | 品質が範囲外 |
| `loras must be an array` | loras が配列でない |
| `loras: maximum 10 LoRAs allowed` | LoRA数が上限超過 |
| `loras[N].url is required and must be a string` | URL未指定 |
| `loras[N].url must start with http:// or https://` | URLスキーム不正 |
| `loras[N].url must point to a .safetensors file` | 拡張子不正 |
| `loras[N].strength must be a number` | strength が数値でない |
| `loras[N].strength must be between -2.0 and 2.0` | strength 範囲外 |
| `Cannot specify both 'loras' and 'lora_url'` | 新旧パラメータ同時指定 |
| `Failed to download LoRA[N]: ...` | LoRAダウンロード失敗 |
| `ComfyUI execution error` | ワークフロー実行エラー |
| `No images generated` | 画像生成失敗 |

## 処理フロー

```
1. クライアント → RunPod API: ジョブ送信
2. RunPod → コンテナ: handler.py 呼び出し
3. handler.py:
   a. 入力バリデーション
   b. Illustrious XL v2.0 ワークフロー構築
   c. ComfyUI WebSocket 接続
   d. プロンプトキューイング
   e. 実行完了待ち
   f. 出力画像取得
   g. JPEG変換 + Base64エンコード
4. RunPod → クライアント: レスポンス返却
```

## パフォーマンス目安

| 条件 | 所要時間 (目安) |
|------|---------------|
| 1024x1024, 28 steps, 8GB GPU | 15-30秒 |
| 768x1024, 28 steps, 8GB GPU | 10-20秒 |
| コールドスタート追加 | +30-60秒 |

※ SDXLベースのためFlux等と比較して軽量・高速。
