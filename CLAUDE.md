# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JPTAKU-Audio is an interactive Japanese tutor companion app that chains: **User text → GPT-4o-mini (LLM) → CosyVoice3 TTS (few-shot) → NVIDIA Audio2Face-3D (facial BlendShapes) → WebSocket → Flutter + Rive (2D character animation)**. The tutor persona is "凛 (Rin)", a friendly Japanese-speaking character.

## Key Commands

```bash
# Install dependencies
uv sync

# Start A2F-3D Docker (first time takes ~5 min for TensorRT compilation)
cd a2f-docker && A2F_3D_MODEL_NAME=claire docker compose up -d

# Start chat server (HTTP :8080 + WebSocket :8765)
cd scripts/a2f_poc && uv run python chat_server.py --port 8080 --ws-port 8765

# Build & serve Flutter web frontend
cd app && flutter build web --pwa-strategy none
python3 -m http.server 7860 --directory build/web

# Standalone A2F test (audio → blendshapes JSON)
cd scripts/a2f_poc && uv run python main.py --a2f ../../assets/reference_voice/tsumugi/tsumugi_04.wav -o blendshapes.json
```

## Architecture

- **scripts/a2f_poc/** — Backend PoC scripts
  - `chat_server.py` — Main server: aiohttp HTTP + websockets WS, LLM → TTS → A2F → WS streaming
  - `main.py` — Standalone A2F-3D gRPC client (audio → blendshapes.json)
  - `ws_server.py` — BlendShape replay server (for testing without A2F)
- **app/** — Flutter frontend
  - `lib/main.dart` — Chat UI + Rive character + WebSocket client + BlendShapeMapper
  - `assets/*.riv` — Rive character files (JcToon facial_expression, Talking Avatar)
  - `web_poc/` — Standalone HTML+JS PoC (no Flutter dependency)
- **a2f-docker/** — NVIDIA Audio2Face-3D Docker Compose setup + configs
- **CosyVoice/** — CosyVoice3 TTS engine (git submodule)
- **pretrained_models/Fun-CosyVoice3-0.5B/** — CosyVoice3 pretrained model
- **assets/reference_voice/** — TTS reference audio samples (few-shot용)
- **run_inference.py** — CosyVoice3 few-shot 단독 추론 스크립트
- **download_model.py** — CosyVoice3 모델 다운로더

## Important Details

- Python 3.12, CUDA 12.x+, NVIDIA GPU required
- A2F-3D runs as Docker container (`nvcr.io/nim/nvidia/audio2face-3d:1.3`), gRPC on port 52000
- `.env` (gitignored) holds `OPENAI_API_KEY` (LLM용) and `NGC_API_KEY` (A2F용)
- A2F outputs PascalCase BlendShape names (JawOpen, MouthSmileLeft) — BlendShapeMapper handles conversion
- JcToon Rive character uses expression categories (Happy/Sad/Surprised/Angry, 0-100 range) — needs aggressive scaling (x200-500) from A2F values (0-0.7 range)
- Talking Avatar character has non-standard inputs (mouth hight, kelopakmata f Slider) — mapping attempted but limited
- Production requires custom Rive character rigged with ARKit BlendShape names for 1:1 mapping
- CosyVoice3 few-shot TTS: 가타카나 변환(pykakasi) 후 inference_zero_shot() 호출, ref_00.wav 레퍼런스 사용
- Comments and docs mix Korean (개발 notes) and Japanese (tutor persona/prompts)

## docs/ — 프로젝트 문서 (작업 시 반드시 업데이트)

작업을 진행할 때마다 아래 4개 파일을 함께 업데이트할 것:

| 파일 | 용도 | 업데이트 시점 |
|------|------|-------------|
| `docs/history.md` | 진행 이력 (시간순) | 작업 완료 시 |
| `docs/todo.md` | 할 일 / 완료 체크리스트 | 작업 시작/완료 시 |
| `docs/issues.md` | 이슈, 리스크, 미결정 사항 | 이슈 발견/해결 시 |
| `docs/product_concept.md` | 제품 컨셉, 아키텍처, 기술 스택 | 방향 변경 시 |
