FROM bizenyakiko/genai-base:1.1

# Install ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI && \
    cd /ComfyUI && \
    pip install -r requirements.txt

# Install ComfyUI-Manager
RUN cd /ComfyUI/custom_nodes && \
    git clone https://github.com/Comfy-Org/ComfyUI-Manager.git && \
    cd ComfyUI-Manager && \
    pip install -r requirements.txt || true

# Install handler dependencies
RUN pip install runpod websocket-client Pillow

# Download Illustrious XL v2.0 (~6.9GB, public, ungated)
RUN mkdir -p /ComfyUI/models/checkpoints && \
    wget -q https://huggingface.co/OnomaAIResearch/Illustrious-XL-v2.0/resolve/main/Illustrious-XL-v2.0.safetensors \
    -O /ComfyUI/models/checkpoints/Illustrious-XL-v2.0.safetensors

# Copy files
COPY handler.py /handler.py
COPY download_lora.py /download_lora.py
COPY model.json /model.json
COPY lora.json /lora.json
COPY extra_model_paths.yaml /ComfyUI/extra_model_paths.yaml
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Fallback dummy LoRA for strength=0 passthrough
RUN touch /ComfyUI/models/loras/default.safetensors

ENTRYPOINT ["/entrypoint.sh"]
