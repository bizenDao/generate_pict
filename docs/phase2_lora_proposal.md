# Phase 2 Proposal: LoRA対応

## 概要

`image_model_deployer` にLoRAローダーノードを追加し、  
デフォルトLoRAをURL指定で差し替えられる仕組みを実装する。

---

## 設計方針

- ワークフロー構造は常にLoRAノードを含む（あり/なしの2パターン不要）
- デフォルトLoRAはブランチごとに`lora.json`で宣言（URL指定）
- リクエスト時に`lora_url`を渡せばデフォルトを上書き
- ダウンロード済みLoRAはNetwork Volumeにキャッシュ（URLのSHA256先頭16文字をファイル名に使用）
- LoRA未設定時はstrength=0でバイパス（ワークフロー分岐なし）

---

## データフロー（改修後）

```
Before:
  1(Checkpoint) ──────────────────────→ 6(KSampler)
  1(Checkpoint) → 2(CLIPSetLastLayer) → 3/4(CLIPTextEncode)

After:
  1(Checkpoint) → 10(LoraLoader) ─────→ 6(KSampler)
  1(Checkpoint) → 10(LoraLoader) → 2(CLIPSetLastLayer) → 3/4(CLIPTextEncode)
```

LoRA未設定時: `strength_model=0, strength_clip=0` → Checkpointをそのままパススルー

---

## 改修内容

### 1. model.json

ノード`10`（LoraLoader）を追加。  
`2`と`6`の参照先を`1`から`10`に変更。  
`lora_name`はComfyUIの`models/loras/`からの相対パスで指定。

```json
{
  "1": { "class_type": "CheckpointLoaderSimple", ... },

  "10": {
    "class_type": "LoraLoader",
    "inputs": {
      "model": ["1", 0],
      "clip":  ["1", 1],
      "lora_name":       "default.safetensors",
      "strength_model":  0.0,
      "strength_clip":   0.0
    }
  },

  "2": {
    "class_type": "CLIPSetLastLayer",
    "inputs": {
      "clip": ["10", 1],          ← ["1", 1] から変更
      "stop_at_clip_layer": -2
    }
  },

  "6": {
    "class_type": "KSampler",
    "inputs": {
      "model": ["10", 0],         ← ["1", 0] から変更
      ...
    }
  }
}
```

**注意**: デフォルトのstrengthは`0.0`。LoRA未設定時はパススルーとなり、  
`default.safetensors`が存在しなくてもエラーにならない  
（ComfyUI LoraLoaderはstrength=0のとき入力をそのまま返す）。

---

### 2. lora.json（新設）

LoRAメタ情報をワークフロー（model.json）とは分離して管理。  
将来のPhase 3でメタ情報が増えても構造が汚れない。

```json
{
  "default_url": "https://huggingface.co/.../your_lora.safetensors",
  "default_strength": 0.8
}
```

`default_url`が空文字列 or キー未設定 → LoRAなしでパススルー動作。

---

### 3. entrypoint.sh

起動時のデフォルトLoRAダウンロードをPythonで統一実行。  
（handler.pyと同じダウンロード関数を使い、手段の不一致を排除）

```bash
# ComfyUI起動前に追加
echo "Preparing default LoRA..."
python3 /download_lora.py
```

**注意**: ダウンロード先は`/ComfyUI/models/loras/`。  
`extra_model_paths.yaml`で`models/loras/`が検索パスに入っているため、  
LoraLoaderはファイル名のみで認識できる。

---

### 4. download_lora.py（新設）

entrypoint.shとhandler.pyの両方から使えるダウンロードユーティリティ。  
一時ファイル → リネームパターンで壊れたキャッシュを防止。

```python
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

LORA_DIR = "/ComfyUI/models/loras"


def lora_filename(url):
    """URLからキャッシュファイル名を生成（SHA256先頭16文字）"""
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{url_hash}.safetensors"


def download_lora(url, dest_dir=LORA_DIR):
    """LoRAをダウンロード。キャッシュ済みならスキップ。
    一時ファイルに書き出してからリネームし、壊れたファイルを防ぐ。
    戻り値: ファイル名（dest_dir からの相対）
    """
    filename = lora_filename(url)
    dest_path = os.path.join(dest_dir, filename)

    if os.path.exists(dest_path):
        logger.info(f"LoRA cached: {filename}")
        return filename

    os.makedirs(dest_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=dest_dir, suffix=".tmp")
    os.close(fd)
    try:
        logger.info(f"Downloading LoRA: {url}")
        urllib.request.urlretrieve(url, tmp_path)
        shutil.move(tmp_path, dest_path)
        logger.info(f"LoRA ready: {filename}")
        return filename
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def download_default():
    """lora.jsonからデフォルトLoRAをダウンロード"""
    config_path = "/lora.json"
    if not os.path.exists(config_path):
        logger.info("No lora.json found, skipping default LoRA")
        return

    with open(config_path) as f:
        config = json.load(f)

    url = config.get("default_url", "")
    if not url:
        logger.info("No default_url in lora.json, skipping")
        return

    filename = download_lora(url)
    # default.safetensorsとしてもアクセスできるようシンボリックリンクを作成
    default_link = os.path.join(LORA_DIR, "default.safetensors")
    if os.path.islink(default_link) or os.path.exists(default_link):
        os.remove(default_link)
    os.symlink(filename, default_link)
    logger.info(f"Default LoRA linked: default.safetensors -> {filename}")


if __name__ == "__main__":
    download_default()
```

---

### 5. handler.py

`lora_url`パラメータを受け取り、ワークフローのLoRAノードを書き換え。  
ダウンロードは`download_lora.py`の関数を呼び出す。  
`lora_name`にはComfyUIが期待する**ファイル名のみ**を設定。

```python
# handler.py 冒頭に追加
from download_lora import download_lora

# --- パラメータ取得・バリデーション（既存パラメータ群の後に追加） ---

lora_url = input_data.get("lora_url")
if lora_url:
    if not isinstance(lora_url, str):
        return {"error": "lora_url must be a string"}
    if not lora_url.startswith(("https://", "http://")):
        return {"error": "lora_url must start with http:// or https://"}
    if not lora_url.endswith(".safetensors"):
        return {"error": "lora_url must point to a .safetensors file"}

lora_strength = input_data.get("lora_strength")
if lora_strength is not None:
    try:
        lora_strength = float(lora_strength)
    except (TypeError, ValueError):
        return {"error": f"lora_strength must be a number, got: {lora_strength}"}
    if not (-2.0 <= lora_strength <= 2.0):
        return {"error": f"lora_strength must be between -2.0 and 2.0, got: {lora_strength}"}

# --- workflowロード後、queue_prompt前に追加 ---

# lora.jsonからデフォルト設定を読み込み
lora_config = {}
if os.path.exists("/lora.json"):
    with open("/lora.json") as f:
        lora_config = json.load(f)

default_strength = float(lora_config.get("default_strength", 0.8))
if lora_strength is None:
    lora_strength = default_strength

if lora_url:
    # リクエストで指定されたLoRA
    try:
        filename = download_lora(lora_url)
    except Exception as e:
        logger.error(f"LoRA download failed: {lora_url} - {e}")
        return {"error": f"Failed to download LoRA: {e}"}
    workflow["10"]["inputs"]["lora_name"]      = filename
    workflow["10"]["inputs"]["strength_model"] = lora_strength
    workflow["10"]["inputs"]["strength_clip"]  = lora_strength
elif lora_config.get("default_url"):
    # デフォルトLoRA（entrypoint.shで既にDL済み）
    workflow["10"]["inputs"]["lora_name"]      = "default.safetensors"
    workflow["10"]["inputs"]["strength_model"] = lora_strength
    workflow["10"]["inputs"]["strength_clip"]  = lora_strength
# else: strength=0.0のまま → パススルー
```

---

## APIパラメータ追加

| パラメータ | 型 | デフォルト | 制約 | 説明 |
|---|---|---|---|---|
| `lora_url` | string | null | `http(s)://`始まり、`.safetensors`終わり | LoRAファイルのURL。未指定時はデフォルトLoRAを使用 |
| `lora_strength` | float | lora.jsonの`default_strength`(0.8) | -2.0 〜 2.0 | LoRAの適用強度（model/clip共通）。負値で逆効果 |

### エラーレスポンス（LoRA関連）

| 条件 | レスポンス |
|---|---|
| `lora_url`が文字列でない | `{"error": "lora_url must be a string"}` |
| URLスキームが不正 | `{"error": "lora_url must start with http:// or https://"}` |
| 拡張子が`.safetensors`でない | `{"error": "lora_url must point to a .safetensors file"}` |
| `lora_strength`が数値でない | `{"error": "lora_strength must be a number, got: ..."}` |
| `lora_strength`が範囲外 | `{"error": "lora_strength must be between -2.0 and 2.0, got: ..."}` |
| LoRAダウンロード失敗 | `{"error": "Failed to download LoRA: ..."}` |

---

## キャッシュ設計

```
/ComfyUI/models/loras/
├── default.safetensors          # → SHA256名ファイルへのsymlink
├── a1b2c3d4e5f67890.safetensors # SHA256先頭16文字でキャッシュ
├── f9e8d7c6b5a43210.safetensors # 別のLoRA
└── ...
```

- SHA256先頭16文字（衝突確率: 2^64分の1で実用上十分）
- ダウンロードは一時ファイル→リネームで原子的に完了
- Network Volumeをマウントすれば同一Workerの再起動をまたいでキャッシュが生きる
- コールドスタート時の初回DL以降はレイテンシなし

---

### 6. Dockerfile

`download_lora.py`、`lora.json`のコピーと、  
strength=0パススルー時のフォールバック用ダミーLoRAを作成。

```dockerfile
# 既存のCOPYブロックに追加
COPY download_lora.py /download_lora.py
COPY lora.json /lora.json

# strength=0時にLoraLoaderがファイル存在を要求する場合のフォールバック
RUN touch /ComfyUI/models/loras/default.safetensors
```

**注意**: `touch`で作成した空ファイルは、LoraLoaderがstrength=0でも  
`lora_name`の存在チェックを行う場合の安全策。  
entrypoint.shでデフォルトLoRAをDLすれば実ファイルで上書きされる。

---

## 改修規模

| ファイル | 変更内容 | 変更行数 |
|---|---|---|
| `model.json` | LoRAノード追加、参照先変更、strength=0.0 | +12行 / 変更2箇所 |
| `lora.json` | 新設: デフォルトLoRA設定 | +4行（新規） |
| `download_lora.py` | 新設: LoRAダウンロード共通ユーティリティ | +50行（新規） |
| `entrypoint.sh` | デフォルトLoRA DL処理追加 | +3行 |
| `handler.py` | lora_urlバリデーション+LoRA注入処理追加 | +30行 |
| `Dockerfile` | COPY 2行 + ダミーLoRA作成 | +3行 |

**合計: 約100行の追加・変更**

---

## 変更点サマリー（初版からの修正）

| # | 初版の問題 | 修正内容 |
|---|---|---|
| 1 | MD5ハッシュ | SHA256先頭16文字に変更 |
| 2 | lora_nameにフルパスを指定 | ファイル名のみを指定（ComfyUI互換） |
| 3 | DL失敗時に壊れたファイルがキャッシュに残る | 一時ファイル→リネームのアトミック書き込み |
| 4 | entrypoint(wget)とhandler(urllib)でDL手段が不一致 | download_lora.pyに統一 |
| 5 | メタ情報がmodel.jsonトップレベルに混在 | lora.jsonに分離 |
| 6 | LoRA未設定時にdefault.safetensors不在でエラー | strength=0.0でパススルー |

---

## ストレージ方針

LoRAファイルの保管先には**S3互換オブジェクトストレージ**を使用する。

### 選定

| サービス | 特徴 |
|---|---|
| **Cloudflare R2** | egress無料、S3互換API、小規模なら最安 |
| **AWS S3** | 定番、RunPodとの相性も問題なし |
| **Backblaze B2** | S3互換、ストレージ単価最安クラス |

LoRAは1ファイル数MB〜数百MBで更新頻度は低い。egressコストが支配的になるため、
コールドスタートのたびにDLが走ることを考慮すると**Cloudflare R2（egress無料）**が第一候補。

### GitHubを使わない理由

- ファイル上限100MB（50MB超で警告）
- Git履歴の肥大化
- Git LFS無料枠: 帯域1GB/月（コールドスタートのたびに消費）

### Hugging Faceを使わない理由

- 公開モデルのホスティングには最適だが、ユーザーのカスタムLoRA管理にはコントロールしづらい
- Phase 3で学習済みLoRAの書き出し先が必要 → どのみず自前ストレージが要る
- S3互換ならpresigned URLを叩くだけで`download_lora.py`の変更不要

---

## 検証用LoRAセット

パイプラインの動作検証用に、公開済みの軽量LoRAを流用する。  
自前学習は不要。目的は「LoRAが正しく読み込まれ、出力に反映されること」の視覚的確認。

### 採用: ntc-ai SDXL LoRA Sliders

- **ライセンス**: MIT
- **ベースモデル**: stabilityai/stable-diffusion-xl-base-1.0（SDXL互換）
- **ファイルサイズ**: 各8.38MB
- **特徴**: スタイル変化が一目でわかるスライダーLoRA。正の重みで効果適用、負の重みで逆方向。

### 検証用3種

| 役割 | LoRA | 効果 | URL |
|---|---|---|---|
| デフォルト | oil-painting | 油彩風（デフォルトLoRA動作確認） | `ntc-ai/SDXL-LoRA-slider.oil-painting` |
| テストA | watercolor | 水彩風（差し替え検証） | `ntc-ai/SDXL-LoRA-slider.watercolor` |
| テストB | high-contrast | 高コントラスト（差し替え検証） | `ntc-ai/SDXL-LoRA-slider.high-contrast` |

DL URL例: `https://huggingface.co/ntc-ai/SDXL-LoRA-slider.oil-painting/resolve/main/oil%20painting.safetensors`

### ストレージ

**暫定**: cielと同一サーバーに配置して配信（3ファイル合計約25MBなので負担なし）  
**本番**: S3/R2に移行。`lora.json`のURLを差し替えるだけで切り替え完了。

### 検証フロー

```
1. lora_url未指定 → oil-painting適用 → 油彩風で出力
2. lora_url=watercolor → 水彩風で出力 → スタイルが変わったことを目視確認
3. lora_url=high-contrast → 高コントラストで出力 → 別のスタイルに変わることを確認
```

これにより、LoRAパイプライン全体（DL→キャッシュ→ワークフロー注入→生成）を
自前学習なし・最小コストで端到端検証できる。

### 注意: SDXL互換性

ntc-aiスライダーはSDXL base向けに学習されている。  
Nova 3DCG XL Illustrious v3.0はSDXL派生モデルのため互換性は高いが、
効果の出方が本家SDXLと異なる可能性がある。  
検証時に効果が弱い場合はstrengthを上げて調整する。

---

## Phase 2.1: 複数LoRA対応（実装済み）

Phase 2の単一LoRA対応を拡張し、配列で最大10個のLoRAをスタックできるようにした。

### 変更点

- 新パラメータ `loras`: `[{url, strength}, ...]` の配列形式
- LoraLoaderノードを動的にチェーン: `Checkpoint → LoRA1 → LoRA2 → ... → LoRAn → KSampler/CLIP`
- レスポンスの `lora`（単一オブジェクト）を `loras`（配列）に変更
- レガシー互換: `lora_url` + `lora_strength` は内部的に1要素配列に変換
- `loras` と `lora_url` の同時指定はエラー
- LoRA未指定時はノード10を削除し、Checkpointから直接接続（パススルー）

### データフロー（複数LoRA）

```
1(Checkpoint) → 10(LoRA1) → 11(LoRA2) → ... → 2(CLIPSetLastLayer) → 3/4(CLIPTextEncode)
1(Checkpoint) → 10(LoRA1) → 11(LoRA2) → ... → 6(KSampler)
```

---

## 今後のPhase 3に向けた布石

今回の設計はLoRA学習パイプラインへの拡張を想定済み。

```
Phase 2（今回）
  ユーザーが自前のLoRAをURLで持ち込んで生成

Phase 3
  学習ジョブをRunPod Serverlessで受け付け
  → 学習済みLoRAをユーザー指定ストレージに書き出し
  → そのURLをPhase 2のlora_urlに渡すだけで生成に使える
```

学習とデプロイのインターフェースがURLで統一されるため、  
Phase 2を正しく作ればPhase 3はほぼそのまま繋がる。
