# デプロイ・テストガイド

## 前提条件

- Docker がインストール済み
- DockerHub アカウント (`bizenyakiko`)
- RunPod アカウント + API キー

## 1. Docker イメージのビルド

```bash
cd /Users/goodsun/develop/bizeny/generate_pict

# ビルド（モデルダウンロードを含むため10〜20分程度）
docker build -t bizenyakiko/generate-pict:latest .
```

### ビルド時の注意

- Pony Diffusion V6 XL: 約6.5GB
- ComfyUI + 依存パッケージ: 約2GB
- **合計: 約9GBのダウンロード**
- すべてのモデルは **public**（認証不要）

### モデル配信元ごとのビルド方式

モデルの配信元によって、Dockerイメージへのチェックポイントの含め方が異なる。詳細は [specification.md](specification.md#デプロイ要件) を参照。

| 配信元 | 方式 | トークン |
|--------|------|---------|
| HuggingFace (ungated) | ビルド時DL（`RUN wget`） | 不要 |
| HuggingFace (gated) | ビルド時DL（`--mount=type=secret`） | `HF_TOKEN`（ビルド時のみ） |
| Civitai (Early Access) | 起動時DL（entrypoint） | `CIVITAI_API_TOKEN`（RunPod環境変数） |

認証付きモデルを `RUN wget --header "Authorization: ..."` でビルドすると、トークンがDockerイメージのレイヤーに焼き込まれ、イメージ共有時に漏洩するリスクがある。gatedモデルにはBuildKit secret、Civitaiモデルには起動時DLを使うこと。

## 2. DockerHub へプッシュ

```bash
docker login
docker push bizenyakiko/generate-pict:latest
```

## 3. RunPod Serverless Endpoint の作成

### RunPod Console での設定

1. https://www.runpod.io/console/serverless にアクセス
2. **New Endpoint** をクリック
3. 以下を設定:

| 設定項目 | 値 |
|---------|-----|
| Endpoint Name | `generate-pict` |
| Container Image | `bizenyakiko/generate-pict:latest` |
| Container Disk | 30 GB |
| GPU | NVIDIA 8GB+ (RTX 3070 等) |
| GPU Count | 1 |
| Max Workers | 1（必要に応じて増加） |
| Idle Timeout | 5s（コスト優先）/ 300s（レスポンス優先） |

4. **Deploy** をクリック

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
| Network timeout | ダウンロード失敗 | 再実行（約9GBのダウンロード） |

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
