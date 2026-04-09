# Stage 1: Download checkpoint (this layer is discarded, so the token never leaks)
FROM alpine:3.20 AS downloader
ARG CIVITAI_API_TOKEN
RUN apk add --no-cache wget
RUN mkdir -p /models && \
    wget -q "https://civitai.com/api/download/models/2824082?token=${CIVITAI_API_TOKEN}" \
      -O /models/UnholyDesireMixSinisterAesthetic_V8.safetensors && \
    echo "Downloaded $(du -h /models/UnholyDesireMixSinisterAesthetic_V8.safetensors | cut -f1)"

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

# Copy checkpoint from downloader stage (token is NOT in this layer)
RUN mkdir -p /ComfyUI/models/checkpoints
COPY --from=downloader /models/UnholyDesireMixSinisterAesthetic_V8.safetensors \
     /ComfyUI/models/checkpoints/UnholyDesireMixSinisterAesthetic_V8.safetensors

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
