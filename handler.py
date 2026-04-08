"""
RunPod Serverless Handler for Pony Diffusion V6 XL Image Generation
Text prompt -> Generated image (JPEG, Base64)
"""

import runpod
import json
import urllib.request
import urllib.parse
import os
import sys
import time
import base64
import uuid
import shutil
import traceback
import logging
import websocket

from download_lora import download_lora

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SERVER_ADDRESS = os.environ.get("SERVER_ADDRESS", "127.0.0.1")
COMFYUI_PORT = "8188"

DEFAULT_NEGATIVE_PROMPT = (
    "score_1, score_2, score_3, lowres, bad anatomy, bad hands, text, error, "
    "missing fingers, extra digit, fewer digits, cropped, worst quality, "
    "low quality, jpeg artifacts, signature, watermark, username, blurry"
)


def to_nearest_multiple_of_8(value, name="value"):
    """Round value to nearest multiple of 8 with validation."""
    try:
        value = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got: {value}")
    if value < 64 or value > 2048:
        raise ValueError(f"{name} must be between 64 and 2048, got: {value}")
    return round(value / 8) * 8


def wait_for_comfyui():
    """Wait for ComfyUI HTTP server to be ready."""
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/system_stats"
    for attempt in range(180):
        try:
            req = urllib.request.Request(url)
            urllib.request.urlopen(req, timeout=5)
            logger.info(f"ComfyUI ready after {attempt + 1} attempts")
            return True
        except Exception:
            if (attempt + 1) % 30 == 0:
                logger.info(f"Waiting for ComfyUI... ({attempt + 1}/180)")
            time.sleep(1)
    raise RuntimeError("ComfyUI failed to start within 180 seconds")


def connect_websocket():
    """Connect to ComfyUI WebSocket."""
    client_id = str(uuid.uuid4())
    ws_url = f"ws://{SERVER_ADDRESS}:{COMFYUI_PORT}/ws?clientId={client_id}"
    for attempt in range(36):
        try:
            ws = websocket.WebSocket()
            ws.connect(ws_url, timeout=10)
            logger.info(f"WebSocket connected after {attempt + 1} attempts")
            return ws, client_id
        except Exception as e:
            if (attempt + 1) % 6 == 0:
                logger.warning(f"WebSocket retry {attempt + 1}/36: {e}")
            time.sleep(5)
    raise RuntimeError("WebSocket connection failed after 36 attempts (3 minutes)")


def queue_prompt(workflow, client_id):
    """Queue a prompt to ComfyUI."""
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/prompt"
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_history(prompt_id):
    """Get execution history from ComfyUI."""
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/history/{prompt_id}"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())


def get_image(filename, subfolder, folder_type):
    """Get generated image from ComfyUI."""
    params = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder, "type": folder_type})
    url = f"http://{SERVER_ADDRESS}:{COMFYUI_PORT}/view?{params}"
    req = urllib.request.Request(url)
    resp = urllib.request.urlopen(req)
    return resp.read()


def handler(job):
    """RunPod serverless handler."""
    job_id = job.get("id", "unknown")
    input_data = job.get("input", {})

    logger.info(f"Job started: {job_id}")

    try:
        prompt = input_data.get("prompt", "")
        if not prompt:
            return {"error": "prompt is required"}

        # Append quality tags unless disabled
        if not input_data.get("no_quality_tags", False):
            prompt = f"score_9, score_8_up, score_7_up, {prompt}"

        negative_prompt = input_data.get("negative_prompt", DEFAULT_NEGATIVE_PROMPT)

        width = to_nearest_multiple_of_8(input_data.get("width", 1024), "width")
        height = to_nearest_multiple_of_8(input_data.get("height", 1024), "height")

        try:
            steps = int(input_data.get("steps", 20))
            seed = int(input_data.get("seed", 42))
            cfg = float(input_data.get("cfg", 2.5))
            quality = int(input_data.get("quality", 90))
        except (TypeError, ValueError) as e:
            return {"error": f"Invalid parameter type: {e}"}

        if not (1 <= steps <= 100):
            return {"error": f"steps must be between 1 and 100, got: {steps}"}
        if not (1 <= quality <= 100):
            return {"error": f"quality must be between 1 and 100, got: {quality}"}

        # --- LoRA parameters: accept both legacy (lora_url) and new (loras array) ---
        loras_input = input_data.get("loras")
        lora_url = input_data.get("lora_url")

        if loras_input is not None and lora_url is not None:
            return {"error": "Cannot specify both 'loras' and 'lora_url'. Use 'loras' array."}

        # Normalise to list of {url, strength}
        lora_entries = []
        if loras_input is not None:
            if not isinstance(loras_input, list):
                return {"error": "loras must be an array"}
            if len(loras_input) > 10:
                return {"error": "loras: maximum 10 LoRAs allowed"}
            for i, entry in enumerate(loras_input):
                if not isinstance(entry, dict):
                    return {"error": f"loras[{i}] must be an object with 'url' field"}
                url = entry.get("url")
                if not url or not isinstance(url, str):
                    return {"error": f"loras[{i}].url is required and must be a string"}
                if not url.startswith(("https://", "http://")):
                    return {"error": f"loras[{i}].url must start with http:// or https://"}
                if not url.endswith(".safetensors"):
                    return {"error": f"loras[{i}].url must point to a .safetensors file"}
                strength = entry.get("strength")
                if strength is not None:
                    try:
                        strength = float(strength)
                    except (TypeError, ValueError):
                        return {"error": f"loras[{i}].strength must be a number, got: {strength}"}
                    if not (-2.0 <= strength <= 2.0):
                        return {"error": f"loras[{i}].strength must be between -2.0 and 2.0, got: {strength}"}
                lora_entries.append({"url": url, "strength": strength})
        elif lora_url is not None:
            # Legacy single LoRA support
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
            lora_entries.append({"url": lora_url, "strength": lora_strength})

        logger.info(f"Parameters: {width}x{height}, steps={steps}, seed={seed}, cfg={cfg}")

        with open("/model.json", "r") as f:
            workflow = json.load(f)

        # Extract model metadata before sending to ComfyUI
        model_name = workflow.pop("_meta", {}).get("model_name", "unknown")

        workflow["3"]["inputs"]["text"] = prompt
        workflow["4"]["inputs"]["text"] = negative_prompt
        workflow["5"]["inputs"]["width"] = width
        workflow["5"]["inputs"]["height"] = height
        workflow["6"]["inputs"]["seed"] = seed
        workflow["6"]["inputs"]["steps"] = steps
        workflow["6"]["inputs"]["cfg"] = cfg

        # LoRA injection
        lora_config = {}
        if os.path.exists("/lora.json"):
            with open("/lora.json") as f:
                lora_config = json.load(f)

        default_strength = float(lora_config.get("default_strength", 0.8))

        # If no user LoRAs and default exists, use it
        if not lora_entries and lora_config.get("default_url"):
            lora_entries.append({"url": None, "strength": None, "_default": True})

        # Resolve strengths
        for entry in lora_entries:
            if entry.get("strength") is None:
                entry["strength"] = default_strength

        # Filter out strength=0 entries
        lora_entries = [e for e in lora_entries if e["strength"] != 0]

        lora_infos = []

        if not lora_entries:
            logger.info("No LoRAs to apply (none specified or all strength=0)")
        else:
            # Download all LoRAs and build chain
            filenames = []
            for i, entry in enumerate(lora_entries):
                if entry.get("_default"):
                    filenames.append("default.safetensors")
                    default_path = os.path.join("/ComfyUI/models/loras", "default.safetensors")
                    lora_size = os.path.getsize(default_path) / (1024 * 1024) if os.path.exists(default_path) else None
                    lora_infos.append({
                        "used": True, "source": "default",
                        "url": lora_config["default_url"],
                        "strength": entry["strength"],
                        "size_mb": round(lora_size, 2) if lora_size else None,
                    })
                    logger.info(f"Default LoRA [{i}], strength={entry['strength']}")
                else:
                    try:
                        filename = download_lora(entry["url"])
                    except Exception as e:
                        logger.error(f"LoRA download failed: {entry['url']} - {e}")
                        return {"error": f"Failed to download LoRA[{i}]: {e}"}
                    filenames.append(filename)
                    lora_path = os.path.join("/ComfyUI/models/loras", filename)
                    lora_size = os.path.getsize(lora_path) / (1024 * 1024) if os.path.exists(lora_path) else None
                    lora_infos.append({
                        "used": True, "source": "user",
                        "url": entry["url"],
                        "strength": entry["strength"],
                        "size_mb": round(lora_size, 2) if lora_size else None,
                    })
                    logger.info(f"LoRA [{i}]: {filename}, strength={entry['strength']}")

            # Build chained LoraLoader nodes in workflow
            # First LoRA node (10) takes input from checkpoint (1)
            # Subsequent nodes (11, 12, ...) chain from previous LoRA node
            # Last node's outputs connect to CLIPSetLastLayer (2) and KSampler (6)
            for i, (filename, entry) in enumerate(zip(filenames, lora_entries)):
                node_id = str(10 + i)
                prev_node = str(10 + i - 1) if i > 0 else "1"

                workflow[node_id] = {
                    "class_type": "LoraLoader",
                    "inputs": {
                        "model": [prev_node, 0],
                        "clip": [prev_node, 1],
                        "lora_name": filename,
                        "strength_model": entry["strength"],
                        "strength_clip": entry["strength"],
                    },
                }

            # Point downstream nodes to the last LoRA node
            last_lora_node = str(10 + len(filenames) - 1)
            workflow["2"]["inputs"]["clip"] = [last_lora_node, 1]
            workflow["6"]["inputs"]["model"] = [last_lora_node, 0]

        # Remove the template node 10 if no LoRAs applied (passthrough)
        if not lora_entries and "10" in workflow:
            del workflow["10"]
            workflow["2"]["inputs"]["clip"] = ["1", 1]
            workflow["6"]["inputs"]["model"] = ["1", 0]

        wait_for_comfyui()
        ws, client_id = connect_websocket()

        try:
            result = queue_prompt(workflow, client_id)
            prompt_id = result.get("prompt_id")
            if not prompt_id:
                return {"error": f"Failed to queue prompt: {result}"}

            logger.info(f"Queued prompt: {prompt_id}")

            while True:
                msg = ws.recv()
                if isinstance(msg, str):
                    data = json.loads(msg)
                    msg_type = data.get("type")
                    if msg_type == "executing":
                        exec_data = data.get("data", {})
                        node = exec_data.get("node")
                        if exec_data.get("prompt_id") == prompt_id:
                            if node is None:
                                logger.info("Execution completed")
                                break
                            else:
                                logger.info(f"Executing node: {node}")
                    elif msg_type == "execution_error":
                        error_data = data.get("data", {})
                        logger.error(f"Execution error: {error_data}")
                        return {"error": f"ComfyUI execution error: {error_data}"}

            history = get_history(prompt_id)
            if prompt_id not in history:
                return {"error": "No history found for prompt"}

            outputs = history[prompt_id].get("outputs", {})
            save_node = outputs.get("8", {})
            images = save_node.get("images", [])
            if not images:
                return {"error": "No images generated"}

            image_info = images[0]
            image_data = get_image(
                image_info["filename"],
                image_info.get("subfolder", ""),
                image_info.get("type", "output")
            )

            from PIL import Image
            import io

            img = Image.open(io.BytesIO(image_data))
            if img.mode == "RGBA":
                img = img.convert("RGB")

            jpeg_buffer = io.BytesIO()
            img.save(jpeg_buffer, format="JPEG", quality=quality)
            jpeg_data = jpeg_buffer.getvalue()

            b64_image = base64.b64encode(jpeg_data).decode("utf-8")

            logger.info(f"Job completed: {job_id} (output {len(jpeg_data)} bytes)")
            return {
                "image": f"data:image/jpeg;base64,{b64_image}",
                "model": model_name,
                "loras": lora_infos,
            }

        finally:
            ws.close()

    except Exception as e:
        logger.error(f"Job failed: {job_id} - {e}")
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
