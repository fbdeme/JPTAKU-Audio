#!/bin/bash
# CosyVoice3 + DyStream 환경 구축 스크립트 (Linux / Ubuntu / vast.ai 용)
# CUDA 12.1 권장
# 사용법: bash setup_vastai.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "  JPTAKU-Audio Setup (vast.ai / Ubuntu GPU)"
echo "=================================================="
echo ""

# 1. 시스템 의존성 설치 (ffmpeg 등)
echo "[1/5] 시스템 의존성 업데이트 및 설치..."
sudo apt-get update -y || echo "  [WARN] sudo apt-get update 에 실패했거나 권한이 없습니다. 진행합니다."
sudo apt-get install -y ffmpeg git || echo "  [WARN] 패키지 설치 실패 (root가 아닐 수 있음). 이미 설치되어 있다면 무방합니다."

# 2. Python 버전 및 venv 확인
echo ""
echo "[2/5] 가상환경(venv) 생성..."
if [ ! -d "venv" ]; then
    python3 -m venv venv || {
        echo "  [ERROR] python3-venv 패키지가 없을 수 있습니다. sudo apt-get install python3-venv 를 실행하세요."
        exit 1
    }
    echo "  venv 생성 완료."
else
    echo "  venv 이미 존재합니다. 스킵."
fi

# venv 활성화
source venv/bin/activate

# 3. pip 업그레이드
echo ""
echo "[3/5] pip 업그레이드..."
pip install --quiet --upgrade pip setuptools wheel

# 4. 패키지 설치
echo ""
echo "[4/5] 패키지 설치 (시간이 걸릴 수 있습니다)..."

# PyTorch (CUDA 12.1 for NVIDIA GPUs)
echo "  - PyTorch (CUDA) 설치 중..."
pip install --quiet torch==2.3.1 torchaudio==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121

# 나머지 패키지
echo "  - 기타 의존성 설치 중..."
pip install --quiet \
    conformer==0.3.2 \
    diffusers==0.29.0 \
    hydra-core==1.3.2 \
    HyperPyYAML==1.2.3 \
    inflect==7.3.1 \
    librosa==0.10.2 \
    lightning==2.2.4 \
    networkx==3.1 \
    "numpy==1.26.4" \
    omegaconf==2.3.0 \
    onnx==1.16.0 \
    "onnxruntime==1.18.0" \
    openai-whisper==20231117 \
    "protobuf==4.25" \
    "pyarrow==18.1.0" \
    "pydantic==2.7.0" \
    "pyworld==0.3.4" \
    rich==13.7.1 \
    soundfile==0.12.1 \
    "transformers==4.51.3" \
    "x-transformers==2.11.24" \
    wetext==0.0.4 \
    wget==3.2 \
    datasets \
    huggingface_hub \
    gradio==5.4.0 \
    pykakasi

# CosyVoice Python 패키지 경로 등록
echo "  - CosyVoice 경로 등록..."
COSYVOICE_PATH="$PROJECT_DIR/CosyVoice"
MATCHA_PATH="$PROJECT_DIR/CosyVoice/third_party/Matcha-TTS"

SITE_PKG=$(python -c "import site; print(site.getsitepackages()[0])")
echo "$COSYVOICE_PATH" > "$SITE_PKG/cosyvoice_local.pth"
echo "$MATCHA_PATH" >> "$SITE_PKG/cosyvoice_local.pth"
echo "  경로 등록 완료: $SITE_PKG/cosyvoice_local.pth"

# 5. 서브모듈 초기화
echo ""
echo "[5/5] Git Submodule 업데이트..."
if [ -d ".git" ]; then
    git submodule update --init --recursive
else
    echo "  [WARN] .git 디렉토리가 없습니다. 서브모듈(CosyVoice, DyStream)이 제대로 클론되었는지 확인하세요."
fi

echo ""
echo "=================================================="
echo "  설치 완료! 다음 단계를 진행하세요:"
echo "=================================================="
echo "  source venv/bin/activate"
echo "  python download_model.py"
echo "  # (테스트) python poc_pipeline.py --text '테스트' --ref_audio '...' --ref_text '...' --image '...'"
echo "=================================================="
