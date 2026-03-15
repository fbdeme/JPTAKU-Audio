# DyStream 테스트 및 실행 가이드 (Vast.ai 환경)

본 저장소의 기본 `setup.sh` 와 `requirements.txt` 는 **Mac(Apple Silicon) 환경에서의 CosyVoice3 구동**을 최우선 목적으로 세팅되어 있습니다.

Vast.ai (Ubuntu + NVIDIA GPU) 서버에서 DyStream 통합 파이프라인(`poc_dystream_pipeline.py`)을 실제 모델로 구동하려면 다음 **추가적인 의존성 설치 및 환경 설정**이 필요합니다.

## 1. 사전 요구사항 (Prerequisites)
Vast.ai 인스턴스 초기화 시 다음 환경을 갖춘 템플릿을 권장합니다:
- **OS**: Ubuntu 22.04 LTS
- **CUDA**: 11.8 또는 12.1 이상
- **Python**: 3.10

## 2. DyStream 패키지 추가 설치 (Vast.ai 전용)
기존의 CosyVoice3 패키지에 더해, 비전 처리 및 모델 렌더링을 위한 라이브러리를 추가해야 합니다.
Vast.ai 터미널(가상환경 내부)에서 아래 명령어를 실행하세요.

```bash
# 1. 시스템 필요 라이브러리 설치 (FFmpeg 및 OpenCV용)
sudo apt-get update
sudo apt-get install -y ffmpeg libsm6 libxext6 libgl1-mesa-glx

# 2. 파이썬 비전 및 미디어 라이브러리 설치
pip install opencv-python-headless mediapipe moviepy accelerate

# 3. DyStream 모델 리포지토리 클론 및 설치 (실제 모델 연동 시)
# git clone https://github.com/StartHua/DyStream.git
# cd DyStream && pip install -r requirements.txt
```

## 3. PoC 파이프라인 실행
1. `poc_dystream_pipeline.py` 스크립트를 열어 `CosyVoice3GPU` 클래스와 `DyStreamGPU` 클래스의 코드를 **실제 모델 Inference 코드**로 치환합니다.
2. 실행할 캐릭터의 기본 이미지 1장을 `assets/` 디렉토리 안에 넣습니다. (예: `assets/sensei_base.jpg`)
3. 스크립트 실행:

```bash
python poc_dystream_pipeline.py
```

## 4. 디버깅 및 메모리 관리
- 스크립트가 실행되는 동안 또 다른 터미널을 열어 `watch -n 1 nvidia-smi`를 입력합니다.
- TTS 처리가 끝난 후(VRAM 사용량 증가) 모델이 지워지면서 VRAM이 확보되고, 다시 DyStream이 로드되며 VRAM을 점유하는 **순차적 OOM 방지 흐름**이 제대로 이뤄지는지 시각적으로 확인합니다.
