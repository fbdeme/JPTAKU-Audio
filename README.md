# JPTAKU-Audio: CosyVoice3 Few-Shot Inference

**CosyVoice3** (`Fun-CosyVoice3-0.5B`) 모델로 **Japanese-Eroge-Voice-V2** 데이터셋을 활용한 Few-shot (Zero-shot) 일본어 음성 합성 프로젝트입니다.

## 프로젝트 구조

```
JPTAKU-Audio/
├── CosyVoice/                  # CosyVoice 레포지토리 (git clone)
├── pretrained_models/          # 다운로드된 모델 (자동 생성)
│   └── Fun-CosyVoice3-0.5B/
├── outputs/                    # 생성된 오디오 파일 (자동 생성)
├── venv/                       # Python 가상환경
├── setup.sh                    # 환경 구축 스크립트
├── download_model.py           # 모델 다운로드 스크립트
├── run_inference.py            # Few-shot 추론 메인 스크립트
└── requirements.txt            # 패키지 의존성
```

## 설치 방법

### 1. 자동 설치 (macOS)
```bash
bash setup.sh
```

### 2. 자동 설치 (vast.ai / Linux GPU 환경)
```bash
bash setup_vastai.sh
```

### 3. 수동 설치
```bash
# Python 3.10 venv 생성
python3.10 -m venv venv
source venv/bin/activate

# PyTorch 설치 (macOS CPU/MPS)
pip install torch==2.3.1 torchaudio==2.3.1 --index-url https://download.pytorch.org/whl/cpu
# 배포 환경 (GPU)라면 아래 명령어로 설치하세요:
# pip install torch==2.3.1 torchaudio==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121

# 기타 의존성 설치
pip install -r requirements.txt
```

## 모델 다운로드

```bash
source venv/bin/activate
python download_model.py
```

> 모델 크기: 약 3~5GB. HuggingFace에서 자동 다운로드됩니다.
> 인터넷 연결이 필요하며, 필요시 `huggingface-cli login`을 먼저 실행하세요.

## 추론 실행

```bash
source venv/bin/activate

# 기본 실행 (데이터셋에서 3개 샘플 추론)
python run_inference.py

# 샘플 수 지정
python run_inference.py --num_samples 5

# 특정 합성 텍스트 지정
python run_inference.py --target_text "こんにちは、今日はいい天気ですね。" --num_samples 3

# 데이터셋 offset 지정 (다른 화자 샘플 사용)
python run_inference.py --dataset_offset 100 --num_samples 3
```

## 옵션 설명

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--num_samples` | 3 | 추론할 샘플 수 |
| `--output_dir` | `outputs` | 출력 디렉토리 |
| `--model_dir` | `pretrained_models/Fun-CosyVoice3-0.5B` | 모델 경로 |
| `--target_text` | None | 합성할 텍스트 (미지정시 레퍼런스 텍스트 사용) |
| `--dataset_split` | `train` | 데이터셋 split |
| `--dataset_offset` | 0 | 데이터셋 시작 offset |

## 데이터셋 정보

**NandemoGHS/Japanese-Eroge-Voice-V2**
- 총 클립 수: 1,033,142개
- 총 오디오: 약 2,657시간
- 평균 길이: 9.26초
- 컬럼: `audio`, `text`, `text_source`, `sampling_rate`, `char_id`

## Few-shot 추론 원리

CosyVoice3의 **Zero-shot Voice Cloning** 기능을 활용합니다:
1. 데이터셋에서 **reference audio** (2~30초)와 **prompt text** 추출
2. `inference_zero_shot()` 호출: 레퍼런스 화자의 음색/운율을 학습
3. `target_text`를 레퍼런스 화자의 목소리로 합성
4. `outputs/*.wav`에 저장

## 요구사항

- macOS (Apple Silicon / Intel)
- Python 3.10
- RAM 8GB+ (16GB 권장)
- 저장공간 10GB+
