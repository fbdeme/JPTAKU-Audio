# JPTAKU-Audio: Interactive Japanese Tutor Avatar

Real-time interactive Japanese tutor with anime character animation, powered by:

- **GPT-SoVITS v2ProPlus** - Japanese TTS with zero-shot voice cloning
- **LAM-Audio2Expression** - Audio to ARKit 52 BlendShape prediction
- **THA4** - Talking Head Anime 4 real-time 2D rendering
- **OpenAI GPT-4o-mini** - Japanese tutor LLM

## Architecture

```
User Input (text)
    |
    v
[GPT-4o-mini] --- Japanese tutor response
    |
    v
[GPT-SoVITS v2ProPlus] --- TTS (zero-shot voice cloning, RTF ~0.014)
    |  Reference: VOICEVOX Kasukabe Tsumugi
    v
[LAM-Audio2Expression] --- Audio -> ARKit 52 BlendShapes @ 30fps
    |
    v
[THA4 ifacialmocap converter] --- ARKit 52 -> THA4 45 params
    |
    v
[THA4 Renderer] --- 2D anime animation @ 48fps (distilled) / 12fps (teacher)
    |
    v
Video + Audio output (Gradio web UI)
```

## Quick Start

### Prerequisites

- Linux with NVIDIA GPU (RTX 3090+ recommended)
- Python 3.12
- CUDA 12.x

### 1. Clone and setup

```bash
git clone --recursive https://github.com/<your-username>/JPTAKU-Audio.git
cd JPTAKU-Audio

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create environment and install dependencies
uv sync
```

### 2. Download models

```bash
# GPT-SoVITS pretrained models
uv run python -c "
from huggingface_hub import snapshot_download
snapshot_download('lj1995/GPT-SoVITS', local_dir='GPT-SoVITS/GPT_SoVITS/pretrained_models',
                  allow_patterns=['*.ckpt','*.pth','*.bin','*.json','*.txt','*.model'])
"

# LAM-Audio2Expression
cd LAM_Audio2Expression
uv run python -c "
from huggingface_hub import snapshot_download
snapshot_download('3DAIGC/LAM_audio2exp', local_dir='./')
"
tar -xzf LAM_audio2exp_assets.tar
tar -xzf LAM_audio2exp_streaming.tar
cd ..

# THA4 teacher models
wget -O /tmp/tha4-models.zip "https://www.dropbox.com/scl/fi/7wec0sur7449iqgtlpi3n/tha4-models.zip?rlkey=0f9d1djmbvjjjn09469s1adx8&dl=1"
unzip /tmp/tha4-models.zip -d THA4/data/tha4/

# VOICEVOX reference voice (optional - pre-generated samples included)
# Install VOICEVOX locally and generate reference audio, or use included samples
```

### 3. Setup environment

```bash
# Create .env file
cat > .env << 'EOF'
OPENAI_API_KEY="your-openai-api-key-here"
EOF
```

### 4. Start GPT-SoVITS API server

```bash
cd GPT-SoVITS
uv run python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml
```

### 5. Start interactive tutor

```bash
cd THA4
uv run python app_tutor.py
# Open http://localhost:7860
```

## Project Structure

```
JPTAKU-Audio/
├── THA4/                           # Talking Head Anime 4 (2D rendering)
│   ├── app_tutor.py                # Main interactive tutor app (Gradio)
│   ├── poc_lam_pipeline.py         # LAM -> THA4 pipeline PoC
│   ├── poc_audio_to_anime.py       # DiffPoseTalk -> THA4 pipeline PoC
│   ├── poc_full_pipeline.py        # Full text->speech->animation pipeline
│   ├── src/tha4/                   # THA4 engine (modified for skip_eyebrow)
│   └── data/character_models/      # Distilled character models
├── GPT-SoVITS/                     # Japanese TTS with voice cloning
│   ├── api_v2.py                   # TTS API server
│   └── GPT_SoVITS/pretrained_models/
├── LAM_Audio2Expression/           # Audio to facial expression
│   ├── inference.py
│   └── pretrained_models/
├── CosyVoice/                      # (Legacy) CosyVoice3 TTS
├── DyStream/                       # (Legacy) DyStream video generation
├── SkyReels-A1/                    # (Legacy) SkyReels-A1 video generation
├── assets/
│   ├── character_base.png          # Character image (original)
│   ├── rin_full.png                # Character image (full body, transparent BG)
│   └── reference_voice/            # TTS reference audio
│       ├── tsumugi/                # VOICEVOX Kasukabe Tsumugi samples
│       ├── sbv2_f2/                # Style-Bert-VITS2 F2 samples
│       ├── oneesan/                # Oneesan-style samples
│       └── clean/                  # Clean SBV2-generated samples
├── .env                            # API keys (gitignored)
├── pyproject.toml                  # uv project config
└── README.md
```

## Component Details

### TTS: GPT-SoVITS v2ProPlus

- **License**: MIT
- **Japanese**: Native support via pyopenjtalk g2p
- **Voice cloning**: Zero-shot (5s reference) + Few-shot (1min fine-tune)
- **Speed**: RTF 0.014 on RTX 4090 (v2ProPlus)
- **Current voice**: VOICEVOX Kasukabe Tsumugi (bright, cheerful girl)
- **API**: HTTP server on port 9880

### Expression: LAM-Audio2Expression

- **License**: Apache 2.0
- **Output**: 52 ARKit BlendShape coefficients @ 30fps
- **Speed**: ~0.03s per 10s audio (real-time capable)
- **Streaming**: 1-second chunk processing supported

### Rendering: THA4

- **License**: Code MIT / Models CC-BY-NC-4.0
- **Input**: 512x512 RGBA character image + 45 pose parameters
- **Speed**: 48fps (distilled) / 12fps (teacher model)
- **Modification**: Added `skip_eyebrow` mode to prevent artifacts on certain character styles

### LLM: OpenAI GPT-4o-mini

- Persona: "Rin" - friendly Japanese tutor
- System prompt configurable in `app_tutor.py`
- Responds in Japanese, 50 characters max

## PoC Scripts

| Script | Description |
|--------|-------------|
| `THA4/app_tutor.py` | **Main app** - Interactive tutor with Gradio UI |
| `THA4/poc_lam_pipeline.py` | LAM -> THA4 animation pipeline |
| `THA4/poc_full_pipeline.py` | Text -> TTS -> Expression -> Animation |
| `THA4/poc_audio_to_anime.py` | DiffPoseTalk FLAME -> THA4 bridge |
| `DyStream/run_anime_poc.py` | DyStream anime character PoC |
| `SkyReels-A1/inference_audio_anime.py` | SkyReels-A1 anime bypass |

## Technology Evaluation History

During development, multiple approaches were evaluated:

| Approach | Result |
|----------|--------|
| **DyStream** | Works for real faces, anime causes style corruption (LIA renderer trained on real faces) |
| **SkyReels-A1** | High quality for real faces, MediaPipe blocks anime faces, 2min/4s on RTX 3090 |
| **DiffPoseTalk + THA4** | Works but FLAME PCA coefficients lack semantic meaning for reliable mapping |
| **LAM-A2E + THA4** | Best approach - ARKit 52 BlendShapes are semantic, THA4 has built-in converter |
| **CosyVoice3 TTS** | Chinese text frontend corrupts Japanese pronunciation |
| **GPT-SoVITS TTS** | Native Japanese support, zero-shot cloning, RTF 0.014 |
| **Style-Bert-VITS2** | MOS 4.37 quality but no voice cloning (used for generating clean reference audio) |

## Customization

### Change voice character

Edit `THA4/app_tutor.py`:
```python
REF_AUDIO = "path/to/reference.wav"       # 3-10 second reference audio
REF_PROMPT_TEXT = "transcript of reference"  # What the reference says
```

### Change anime character

Replace `THA4/data/character_models/<name>/character.png` with a 512x512 RGBA image.
For teacher model (any character): use `--teacher` flag.
For distilled model (faster): run THA4 distillation (~30hrs on A6000).

### Change tutor persona

Edit `SYSTEM_PROMPT` in `THA4/app_tutor.py`.

## Requirements

- NVIDIA GPU with 8GB+ VRAM (24GB recommended for all models)
- ~50GB disk space (all models)
- Python 3.12
- CUDA 12.x
