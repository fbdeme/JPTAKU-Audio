#!/bin/bash
# JPTAKU-Audio Full Setup Script
# Reproduces the complete environment from a fresh clone
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=============================================="
echo "  JPTAKU-Audio Full Setup"
echo "=============================================="

# 1. Submodules
echo "[1/7] Initializing git submodules..."
git submodule update --init --recursive

# 2. External repos (not submodules)
echo "[2/7] Cloning external repositories..."
[ -d "GPT-SoVITS" ] || git clone https://github.com/RVC-Boss/GPT-SoVITS.git
[ -d "LAM_Audio2Expression" ] || git clone https://github.com/aigc3d/LAM_Audio2Expression.git
[ -d "THA4" ] || git clone https://github.com/pkhungurn/talking-head-anime-4-demo.git THA4

# 3. Apply THA4 patch (skip_eyebrow modification)
echo "[3/7] Applying THA4 patches..."
if [ -f "pipeline/tha4_mode07_skip_eyebrow.patch" ]; then
    echo "  Manual patch required - see pipeline/tha4_mode07_skip_eyebrow.patch"
fi
# Copy pipeline scripts to THA4
cp pipeline/app_tutor.py THA4/
cp pipeline/poc_lam_pipeline.py THA4/
cp pipeline/poc_audio_to_anime.py THA4/
cp pipeline/poc_full_pipeline.py THA4/
# Symlink model_assets if exists
[ -d "model_assets" ] && ln -sf "$PROJECT_DIR/model_assets" THA4/model_assets

# 4. Python dependencies
echo "[4/7] Installing Python dependencies..."
if command -v uv &>/dev/null; then
    uv sync
else
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
    pip install pyopenjtalk g2p_en pypinyin cn2an LangSegment fast-langdetect funasr==1.0.27 peft ffmpeg-python
    pip install librosa soundfile transformers addict yapf termcolor
    pip install scipy einops omegaconf Pillow
    pip install "gradio<5" openai python-dotenv requests imageio imageio-ffmpeg opencv-python-headless pykakasi
    pip install huggingface_hub modelscope datasets style-bert-vits2
fi

# 5. Download models
echo "[5/7] Downloading pretrained models..."

# GPT-SoVITS models
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('lj1995/GPT-SoVITS', local_dir='GPT-SoVITS/GPT_SoVITS/pretrained_models',
                  allow_patterns=['*.ckpt','*.pth','*.bin','*.json','*.txt','*.model'])
print('GPT-SoVITS models: OK')
"

# LAM-Audio2Expression models
cd LAM_Audio2Expression
python3 -c "
from huggingface_hub import snapshot_download
snapshot_download('3DAIGC/LAM_audio2exp', local_dir='./')
print('LAM models: OK')
"
[ -f "LAM_audio2exp_assets.tar" ] && tar -xzf LAM_audio2exp_assets.tar
[ -f "LAM_audio2exp_streaming.tar" ] && tar -xzf LAM_audio2exp_streaming.tar
cd "$PROJECT_DIR"

# THA4 teacher models
echo "  Downloading THA4 teacher models..."
wget -q "https://www.dropbox.com/scl/fi/7wec0sur7449iqgtlpi3n/tha4-models.zip?rlkey=0f9d1djmbvjjjn09469s1adx8&dl=1" -O /tmp/tha4-models.zip
unzip -o /tmp/tha4-models.zip -d THA4/data/tha4/

# Style-Bert-VITS2 BERT model (for reference audio generation)
python3 -c "
from style_bert_vits2.nlp import bert_models
from style_bert_vits2.constants import Languages
bert_models.load_model(Languages.JP, 'ku-nlp/deberta-v2-large-japanese-char-wwm')
print('SBV2 BERT: OK')
"

# fast_langdetect model
mkdir -p GPT-SoVITS/GPT_SoVITS/pretrained_models/fast_langdetect
python3 -c "
from fast_langdetect import detect
detect('test')
" 2>/dev/null
find /tmp -name "lid.176.bin" -exec cp {} GPT-SoVITS/GPT_SoVITS/pretrained_models/fast_langdetect/ \; 2>/dev/null

# 6. GPT-SoVITS config
echo "[6/7] Creating GPT-SoVITS config..."
cat > /tmp/tts_v2proplus.yaml << 'YAML'
custom:
  bert_base_path: GPT_SoVITS/pretrained_models/chinese-roberta-wwm-ext-large
  cnhuhbert_base_path: GPT_SoVITS/pretrained_models/chinese-hubert-base
  device: cuda
  is_half: true
  t2s_weights_path: GPT_SoVITS/pretrained_models/s1v3.ckpt
  version: v2ProPlus
  vits_weights_path: GPT_SoVITS/pretrained_models/v2Pro/s2Gv2ProPlus.pth
YAML

# 7. Symlink for python
echo "[7/7] Final setup..."
[ -f /usr/local/bin/python ] || ln -sf /usr/bin/python3 /usr/local/bin/python 2>/dev/null || true

echo ""
echo "=============================================="
echo "  Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo "  1. Create .env file:  echo 'OPENAI_API_KEY=your-key' > .env"
echo "  2. Start GPT-SoVITS:  cd GPT-SoVITS && python api_v2.py -a 127.0.0.1 -p 9880 -c /tmp/tts_v2proplus.yaml"
echo "  3. Start tutor app:   cd THA4 && python app_tutor.py"
echo "  4. Open browser:      http://localhost:7860"
