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
    "steps": 20,
    "seed": 42,
    "cfg": 2.5,
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

生成する画像の説明テキスト。Pony系モデルのタグ形式推奨。

```
"1girl, long hair, school uniform, cherry blossoms, detailed background"
```

`no_quality_tags` が false（デフォルト）の場合、自動的に以下が先頭に付与される:
```
score_9, score_8_up, score_7_up
```

### negative_prompt

除外したい要素の指定。未指定時はPony用���フォルト値が使用される。

デフォルト値:
```
score_1, score_2, score_3, lowres, bad anatomy, bad hands, text, error,
missing fingers, extra digit, fewer digits, cropped, worst quality,
low quality, jpeg artifacts, signature, watermark, username, blurry
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
| デフォルト | 20 |
| 推奨範囲 | 16-30 |
| 最小 | 1 |
| 最大 | 100 |

このモデルは8-10ステップでも十分な品質を出せる。

### cfg

Classifier-Free Guidance スケール。高いほどプロンプトに忠実。

| 値 | 説明 |
|----|------|
| デフォルト | 2.5 |
| 推奨範囲 | 2.0-4.0 |

このモデルは低CFGで最適に動作する。

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

`true` にすると品質タグ（score_9 等）の自動付与を無効化する。独自のタグ体系を使いたい場合に利用。

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
    "model": "Unholy Desire Mix - Sinister Aesthetic v8",
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

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `image` | string | Base64エンコードされたJPEG画像（data URI） |
| `model` | string | 使用されたモデル名（`model.json`の`_meta.model_name`から取得） |
| `loras` | array | 使用されたLoRA情報の配列（LoRA未使用時は空配列） |

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

## デプロイ要件

### 環境変数

| 変数名 | 必須 | 説明 |
|--------|------|------|
| `CIVITAI_API_TOKEN` | はい（Early Access期間中） | コンテナ起動時のチェックポイントDLに使用 |

### モデルのダウンロード方式

チェックポイント（約6.5GB）はDockerイメージに含まず、コンテナ初回起動時にCivitai APIからダウンロードする。

#### モデル配信元ごとのダウンロード戦略

| モデル配信元 | 推奨方式 | 理由 |
|------------|---------|------|
| HuggingFace (ungated) | ビルド時DL | 認証不要。イメージに含めればコールドスタートが速い |
| HuggingFace (gated) | ビルド時DL (`--mount=type=secret`) | BuildKit secretでトークンをレイヤーに残さず安全にDL可能 |
| Civitai (Early Access) | 起動時DL | API仕様変更リスクあり。環境変数でトークンを渡す方が運用しやすい |

#### ビルド時DL vs 起動時DL 比較

| 観点 | ビルド時DL | 起動時DL |
|------|----------|---------|
| イメージサイズ | +6.5GB（push/pullが遅い） | 軽量 |
| 認証トークン | `RUN wget`だとレイヤーに残る（`--mount=type=secret`で回避可） | 環境変数で安全に渡せる |
| モデル更新 | フルリビルド+再push必要 | 環境変数やURLの変更のみ |
| コールドスタート | 速い（モデル同梱済み） | 初回はDL時間が加算される |
| 外部依存 | なし（自己完結） | モデル配信元への到達性が必要 |

#### BuildKit secretによるビルド時DL（gatedモデル向け）

```dockerfile
# syntax=docker/dockerfile:1
RUN --mount=type=secret,id=hf_token \
    HF_TOKEN=$(cat /run/secrets/hf_token) && \
    wget --header "Authorization: Bearer $HF_TOKEN" \
    -O /ComfyUI/models/checkpoints/model.safetensors \
    "https://huggingface.co/org/model/resolve/main/model.safetensors"
```

```bash
docker build --secret id=hf_token,env=HF_TOKEN -t myimage .
```

シークレットはビルドキャッシュやイメージレイヤーに残らないため、gatedモデルでも安全にイメージに含められる。

#### 本プロジェクトの選択

Sinister AestheticはCivitaiのEarly Accessモデルであり、起動時DLを採用した。Network Volumeをマウントすれば初回DL後はチェックポイントがキャッシュされ、2回目以降のコールドスタートではDLをスキップできる。

## 処理フロー

```
1. クライアント -> RunPod API: ジョブ送信
2. RunPod -> コンテナ: handler.py 呼び出し
3. handler.py:
   a. 入力バリデーション
   b. Unholy Desire Mix v8 ワークフロー構築
   c. ComfyUI WebSocket 接続
   d. プロンプトキューイング
   e. 実行完了待ち
   f. 出力画像取得
   g. JPEG変換 + Base64エンコード
4. RunPod -> クライアント: レスポンス返却
```

## パフォーマンス目安

| 条件 | 所要時間 (目安) |
|------|---------------|
| 1024x1024, 20 steps, 8GB GPU | 10-25秒 |
| 768x1024, 20 steps, 8GB GPU | 8-18秒 |
| コールドスタート追加 | +30-60秒 |

DPM++ 2Mサンプラーは少ないステップ数でも高品質な結果を出せる。
