"""
LoRA download utility for entrypoint.sh and handler.py.
Atomic write (temp file → rename) prevents corrupted cache entries.
"""

import hashlib
import json
import os
import shutil
import tempfile
import urllib.request
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

LORA_DIR = "/ComfyUI/models/loras"


def lora_filename(url):
    """Generate cache filename from URL (SHA256 first 16 chars)."""
    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{url_hash}.safetensors"


def download_lora(url, dest_dir=LORA_DIR):
    """Download LoRA. Skip if cached.
    Write to temp file then rename to prevent corrupted cache.
    Returns: filename (relative to dest_dir)
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
    """Download default LoRA from lora.json."""
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
    default_link = os.path.join(LORA_DIR, "default.safetensors")
    if os.path.islink(default_link) or os.path.exists(default_link):
        os.remove(default_link)
    os.symlink(filename, default_link)
    logger.info(f"Default LoRA linked: default.safetensors -> {filename}")


if __name__ == "__main__":
    download_default()
