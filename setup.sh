#!/bin/bash
# CosyVoice3 + Japanese-Eroge-Voice-V2 환경 구축 스크립트 (macOS)
# 사용법: bash setup.sh

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "=================================================="
echo "  CosyVoice3 Few-Shot Inference Setup (macOS)"
echo "=================================================="
echo ""

# 1. Python 버전 확인
echo "[1/5] Python 버전 확인..."
if command -v pyenv &>/dev/null; then
    pyenv local 3.10.0 2>/dev/null || true
fi
PYTHON_BIN=$(which python3)
PYTHON_VER=$(python3 --version)
echo "  사용할 Python: $PYTHON_BIN ($PYTHON_VER)"

# 2. venv 생성
echo ""
echo "[2/5] 가상환경(venv) 생성..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
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

# PyTorch (CPU/MPS for macOS)
echo "  - PyTorch 설치 중..."
pip install --quiet torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu

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
    gradio==5.4.0

# CosyVoice Python 패키지 경로 등록
echo "  - CosyVoice 경로 등록..."
COSYVOICE_PATH="$PROJECT_DIR/CosyVoice"
MATCHA_PATH="$PROJECT_DIR/CosyVoice/third_party/Matcha-TTS"

SITE_PKG=$(python -c "import site; print(site.getsitepackages()[0])")
echo "$COSYVOICE_PATH" > "$SITE_PKG/cosyvoice_local.pth"
echo "$MATCHA_PATH" >> "$SITE_PKG/cosyvoice_local.pth"
echo "  경로 등록 완료: $SITE_PKG/cosyvoice_local.pth"

# 5. 완료
echo ""
echo "[5/5] 설치 완료!"
echo ""
echo "=================================================="
echo "  다음 단계:"
echo "=================================================="
echo ""
echo "  # 가상환경 활성화"
echo "  source venv/bin/activate"
echo ""
echo "  # 모델 다운로드 (HuggingFace)"
echo "  python download_model.py"
echo ""
echo "  # Few-shot 추론 실행 (샘플 3개)"
echo "  python run_inference.py --num_samples 3"
echo ""
echo "  # 특정 텍스트로 합성"
echo "  python run_inference.py --target_text '合成したいテキストをここに入力してください。'"
echo ""
