# Stage 1: Download checkpoint (isolates credentials from final image)
FROM alpine:3.20 AS downloader
RUN apk add --no-cache wget
RUN mkdir -p /models && \
    wget -q https://huggingface.co/datasets/John6666/model-mirror-26/resolve/main/nova3DCGXL_illustriousV30.safetensors \
      -O /models/nova3DCGXL_illustriousV30.safetensors && \
    echo "Downloaded $(du -h /models/nova3DCGXL_illustriousV30.safetensors | cut -f1)"

# Stage 2: Build the actual image
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

# Copy checkpoint from downloader stage
RUN mkdir -p /ComfyUI/models/checkpoints
COPY --from=downloader /models/nova3DCGXL_illustriousV30.safetensors \
     /ComfyUI/models/checkpoints/nova3DCGXL_illustriousV30.safetensors

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
