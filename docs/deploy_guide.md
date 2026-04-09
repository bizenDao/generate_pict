# デプロイ・テストガイド

## 前提条件

- Docker がインストール済み
- DockerHub アカウント (`bizenyakiko`)
- RunPod アカウント + API キー
- Civitai APIトークン（Early Access期間中のみ）

## 1. Docker イメージのビルド

```bash
cd /Users/goodsun/develop/ciel-image-generator/bizeny_sinister

docker build -t bizenyakiko/bizeny-sinister:latest .
```

### ビルド時の注意

- チェックポイントはイメージに含まれない（コンテナ起動時にDL）
- ComfyUI + 依存パッケージ: 約2GB
- イメージサイズは bizeny_imd より約6.5GB小さい

### なぜビルド時にモデルを含めないのか

Sinister AestheticはCivitaiの認証付きモデルのため、ビルド時にダウンロードすると `CIVITAI_API_TOKEN` がDockerイメージのレイヤーに残り、イメージを共有した際にトークンが漏洩するリスクがある。起動時DL方式ならトークンはRunPodの環境変数として渡すだけでイメージには一切残らない。

なお、Network Volumeをマウントすれば初回DL後はチェックポイントがキャッシュされ、2回目以降のコールドスタートではDLをスキップできる。

### Civitai APIトークンの取得

1. https://civitai.com にログイン
2. Settings > API Keys
3. 新しいAPIキーを作成

## 2. DockerHub へプッシュ

```bash
docker login
docker push bizenyakiko/bizeny-sinister:latest
```

## 3. RunPod Serverless Endpoint の作成

### RunPod Console での設定

1. https://www.runpod.io/console/serverless にアクセス
2. **New Endpoint** をクリック
3. 以下を設定:

| 設定項目 | 値 |
|---------|-----|
| Endpoint Name | `bizeny-sinister` |
| Container Image | `bizenyakiko/bizeny-sinister:latest` |
| Container Disk | 30 GB |
| GPU | NVIDIA 8GB+ (RTX 3070 等) |
| GPU Count | 1 |
| Max Workers | 1（必要に応じて増加） |
| Idle Timeout | 5s（コスト優先）/ 300s（レスポンス優先） |

4. **Environment Variables** に以下を追加:

| 変数名 | 値 | 説明 |
|--------|-----|------|
| `CIVITAI_API_TOKEN` | (Civitaiで取得したトークン) | モデルDL用（Early Access期間中は必須） |

5. **Network Volume** をマウント（推奨）: チェックポイントがキャッシュされ、2回目以降のコールドスタートでDLスキップ

6. **Deploy** をクリック

### Endpoint ID の取得

デプロイ後、ダッシュボードに表示される Endpoint ID をメモ。

## 4. 環境変数の設定

```bash
cp .env.example .env
```

`.env` を編集:

```
RUNPOD_API_KEY=your-actual-api-key
RUNPOD_ENDPOINT_ID=your-actual-endpoint-id
```

## 5. テスト実行

### txt2img テスト（curl）

```bash
source .env

# ジョブ送信
JOB_ID=$(curl -s -X POST \
  "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/run" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"1girl, long hair, school uniform, cherry blossoms"}}' \
  | jq -r '.id')

echo "Job ID: $JOB_ID"

# ステータス確認
curl -s \
  "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/status/${JOB_ID}" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" | jq .status
```

### 同期実行テスト

```bash
curl -s -X POST \
  "https://api.runpod.ai/v2/${RUNPOD_ENDPOINT_ID}/runsync" \
  -H "Authorization: Bearer ${RUNPOD_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"1girl, sitting, cafe, warm lighting"}}' | jq .
```

## 6. トラブルシューティング

### ビルドが失敗する

| エラー | 原因 | 対処 |
|--------|------|------|
| Disk space | ディスク不足 | `docker system prune` で空き確保 |
| Network timeout | ダウンロード失敗 | 再実行 |

### コンテナ起動時にモデルDLが失敗する

| エラー | 原因 | 対処 |
|--------|------|------|
| CIVITAI_API_TOKEN is required | 環境変数未設定 | RunPodのEnvironment Variablesに追加 |
| 403 Forbidden | トークン無効/期限切れ | Civitaiでトークンを再発行 |
| Network timeout | DL失敗 | コンテナ再起動で再試行 |

### ジョブが FAILED ��なる

| エラーメッセージ | 原因 | 対処 |
|-----------------|------|------|
| ComfyUI failed to start | コンテナ起動失敗 | RunPod ログを確認、ディスク容量を増やす |
| No images generated | ワークフロー実行失敗 | プロンプトやパラメータを確認 |
| OOM (Out of Memory) | VRAM不足 | 解像度を下げる (768x768)、8GB以上のGPU推奨 |
| ComfyUI execution error | ノード実行エラー | ComfyUIのバージョン互換性を確認 |

### コールドスタートが遅い

- **Flash Boot** を有効にすると2回目以降が速くなる
- Idle Timeout を増やす（ウォームスタート維持）
- Min Workers を 1 にする（常時稼働、コスト増）
