# generate_pict

[日本語](../README.md)

3DCG/anime image generation API using Nova 3DCG XL Illustrious v3.0 on RunPod Serverless.

## Overview

Generate high-quality 3DCG-style anime and illustration images from text prompts. Uses the Nova 3DCG XL Illustrious v3.0 model (SDXL-based) on a ComfyUI backend, deployed on RunPod Serverless.

## Features

- Text-to-image 3DCG/anime generation
- Danbooru tag + natural language support
- Automatic quality tags (masterpiece, best quality, absurdres)
- Multiple LoRA stacking (up to 10) via URL
- JPEG output with configurable quality

## API Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prompt` | string | (required) | Generation prompt |
| `negative_prompt` | string | (auto) | Negative prompt (includes Pony score_1/2/3) |
| `width` | int | 1024 | Image width (auto-rounded to nearest 8) |
| `height` | int | 1024 | Image height (auto-rounded to nearest 8) |
| `steps` | int | 25 | Inference steps |
| `seed` | int | 42 | Random seed |
| `cfg` | float | 4.0 | CFG scale |
| `quality` | int | 90 | JPEG quality (1-100) |
| `no_quality_tags` | bool | false | Disable automatic quality tag prepending |
| `loras` | array | (none) | Array of LoRA objects `{url, strength}` (max 10) |
| `lora_url` | string | (none) | Legacy: single LoRA URL (cannot use with `loras`) |
| `lora_strength` | float | 0.8 | Legacy: single LoRA strength (-2.0 to 2.0) |

## Usage Example

### Basic

```json
{
  "input": {
    "prompt": "1girl, long hair, school uniform, cherry blossoms, detailed background"
  }
}
```

### With multiple LoRAs

```json
{
  "input": {
    "prompt": "1girl, long hair, blue eyes, school uniform, standing, outdoors",
    "loras": [
      {"url": "https://example.com/style.safetensors", "strength": 0.8},
      {"url": "https://example.com/character.safetensors", "strength": 0.6}
    ]
  }
}
```

## Setup

### 1. Build Docker Image

```bash
docker build -t generate-pict .
```

### 2. Deploy to RunPod

Deploy the Docker image as a RunPod Serverless Endpoint.

### 3. Test

```bash
cp .env.example .env
# Set your API key and endpoint ID in .env

curl -s -X POST "https://api.runpod.ai/v2/${ENDPOINT_ID}/runsync" \
  -H "Authorization: Bearer ${API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"input":{"prompt":"1girl, long hair, sunset, detailed"}}'
```

## Architecture

| Component | Details |
|-----------|---------|
| Model | Nova 3DCG XL Illustrious v3.0 (SDXL, ~6.5GB, public) |
| CLIP Skip | 2 |
| Sampler | Euler Ancestral (Normal) |
| Backend | ComfyUI |
| GPU | NVIDIA 8GB+ |
| Output | JPEG (Base64) |
