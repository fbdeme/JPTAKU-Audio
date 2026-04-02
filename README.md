# JPTAKU-Audio: Interactive Japanese Tutor Companion

Real-time interactive Japanese tutor with 2D character animation, powered by:

- **OpenAI GPT-4o-mini** — Japanese tutor LLM (persona: 凛/Rin)
- **OpenAI TTS** — Speech synthesis (PoC; GPT-SoVITS planned for production)
- **NVIDIA Audio2Face-3D** — Audio → ARKit 55 BlendShape prediction
- **Rive** — 2D character animation driven by BlendShape data
- **Flutter** — Cross-platform frontend (Web PoC, Mobile planned)

## Architecture

```
User Input (text)
    |
    v
[GPT-4o-mini] ─── Japanese tutor response (~1.6s)
    |
    v
[OpenAI TTS] ──── Speech synthesis (~1.7s)
    |
    v
[NVIDIA A2F-3D] ─ Audio → ARKit 55 BlendShapes @ 30fps (~2s, Docker local)
    |
    v  (WebSocket, 30fps)
[Flutter + Rive] ─ 2D character expression + audio playback
```

## Quick Start (PoC)

### Prerequisites

- Linux with NVIDIA GPU (RTX 3090+ recommended)
- Python 3.12, CUDA 12.x+
- Docker with NVIDIA container runtime
- Flutter 3.28+ (for building frontend)
- NGC API Key (for A2F-3D Docker image)

### 1. Clone and setup

```bash
git clone https://github.com/fbdeme/JPTAKU-Audio.git
cd JPTAKU-Audio

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv sync
```

### 2. Setup .env

```bash
cat > .env << 'EOF'
OPENAI_API_KEY="your-openai-api-key"
NGC_API_KEY="your-ngc-api-key"
EOF
```

### 3. Start A2F-3D Docker

```bash
# Login to NGC registry
echo $NGC_API_KEY | docker login nvcr.io -u '$oauthtoken' --password-stdin

# Start A2F-3D (first run compiles TensorRT engines, takes ~5 min)
cd a2f-docker
export NGC_API_KEY A2F_3D_MODEL_NAME=claire
docker compose up -d

# Verify: gRPC on port 52000
docker logs a2f-docker-a2f-3d-service-1 2>&1 | tail -3
# Should show: [  global  ] [info] Running...
```

### 4. Start chat server

```bash
cd scripts/a2f_poc
uv run python chat_server.py --port 8080 --ws-port 8765
# HTTP API on :8080, WebSocket on :8765
```

### 5. Start Flutter web frontend

```bash
cd app
flutter build web --pwa-strategy none
python3 -m http.server 7860 --directory build/web
# Open http://localhost:7860
```

### 6. (Remote server) SSH port forwarding

If running on a remote server, forward ports from your local machine:

```bash
ssh -L 7860:localhost:7860 -L 8080:localhost:8080 -L 8765:localhost:8765 user@server
```

Then open `http://localhost:7860` in your browser.

## Project Structure

```
JPTAKU-Audio/
├── app/                              # Flutter frontend
│   ├── lib/main.dart                 # Chat UI + Rive + WebSocket client
│   ├── assets/*.riv                  # Rive character files
│   └── web_poc/                      # Standalone JS PoC (no Flutter)
├── scripts/a2f_poc/                  # Backend PoC scripts
│   ├── chat_server.py                # Chat server (LLM + TTS + A2F + WS)
│   ├── main.py                       # A2F-3D gRPC client (standalone)
│   └── ws_server.py                  # BlendShape replay server
├── a2f-docker/                       # A2F-3D Docker Compose + configs
├── pipeline/                         # Legacy: THA4-based pipeline scripts
├── assets/reference_voice/           # TTS reference audio samples
├── docs/                             # Project docs (history, todo, issues)
├── .env                              # API keys (gitignored)
└── pyproject.toml                    # uv project config
```

## Technology Evaluation History

| Approach | Result |
|----------|--------|
| **NVIDIA A2F-3D + Rive** | **Current** — ARKit BlendShapes → Rive Number Inputs, E2E PoC success |
| **LAM-A2E + THA4** | Previous — worked but LAM lacks benchmarks, THA4 not Flutter-compatible |
| **DyStream** | Anime causes style corruption (LIA renderer trained on real faces) |
| **SkyReels-A1** | MediaPipe blocks anime faces, 2min/4s generation |
| **CosyVoice3 TTS** | Chinese frontend corrupts Japanese pronunciation |
| **GPT-SoVITS TTS** | Native Japanese, RTF 0.014 — planned for production |
| **Live2D** | Poor Flutter support → Rive selected instead |
| **Unity frontend** | Replaced by Flutter for cross-platform mobile |

## Requirements

- NVIDIA GPU with 8GB+ VRAM (24GB recommended)
- Docker with `nvidia` runtime
- Python 3.12, CUDA 12.x+
- OpenAI API key
- NGC API key (free account)
