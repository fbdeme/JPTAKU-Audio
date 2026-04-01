# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

JPTAKU-Audio is an interactive Japanese tutor avatar that chains: **User text → GPT-4o-mini (LLM) → GPT-SoVITS (TTS) → LAM-Audio2Expression (facial BlendShapes) → THA4 (2D anime rendering) → Gradio UI**. The tutor persona is "Rin" (凛), a friendly Japanese-speaking character.

## Key Commands

```bash
# Install dependencies (preferred)
uv sync

# Full environment setup from scratch (clones external repos, downloads models, etc.)
bash scripts/setup_full.sh

# Start GPT-SoVITS TTS API server (must run first, in separate terminal)
cd GPT-SoVITS && uv run python api_v2.py -a 127.0.0.1 -p 9880 -c GPT_SoVITS/configs/tts_infer.yaml

# Start the main interactive tutor app (Gradio on :7860)
cd THA4 && uv run python app_tutor.py
```

## Architecture

- **pipeline/** — Source-of-truth for app and PoC scripts. `setup_full.sh` copies these into `THA4/` at setup time.
  - `app_tutor.py` — Main Gradio app (chat → LLM → TTS → expression → animation loop)
  - `poc_lam_pipeline.py`, `poc_full_pipeline.py`, `poc_audio_to_anime.py` — Standalone PoC pipelines
  - `tha4_mode07_skip_eyebrow.patch` — Patch for THA4 to prevent eyebrow artifacts on certain character styles
- **External repos** (cloned by `setup_full.sh`, gitignored, not submodules):
  - `GPT-SoVITS/` — TTS server (HTTP API on port 9880)
  - `LAM_Audio2Expression/` — Audio → ARKit 52 BlendShape coefficients
  - `THA4/` — 2D anime renderer (512x512 RGBA + 45 pose params)
- **Git submodules** (legacy, kept for reference): `CosyVoice/`, `DyStream/`
- **assets/reference_voice/** — TTS reference audio samples for voice cloning (Kasukabe Tsumugi is the active voice)

## Important Details

- Python 3.12, CUDA 12.x, NVIDIA GPU required (RTX 3090+ recommended, 24GB VRAM for all models)
- `.python-version` says 3.10 (legacy CosyVoice setup) but `pyproject.toml` requires >=3.12 — use 3.12
- GPT-SoVITS runs as a **separate process** (HTTP API), not imported directly
- LAM and THA4 are imported directly into `app_tutor.py` via sys.path manipulation
- `app_tutor.py` stubs out `wx` module at import time to avoid GUI dependency from THA4
- The `.env` file (gitignored) holds `OPENAI_API_KEY`
- The `agent_handoff_to_unity.md` is a handoff spec for a separate Unity frontend project (JPTAKU-Unity)
- Comments and docs mix Korean (개발 notes) and Japanese (tutor persona/prompts)

## docs/ — 프로젝트 문서 (작업 시 반드시 업데이트)

작업을 진행할 때마다 아래 4개 파일을 함께 업데이트할 것:

| 파일 | 용도 | 업데이트 시점 |
|------|------|-------------|
| `docs/history.md` | 진행 이력 (시간순) | 작업 완료 시 |
| `docs/todo.md` | 할 일 / 완료 체크리스트 | 작업 시작/완료 시 |
| `docs/issues.md` | 이슈, 리스크, 미결정 사항 | 이슈 발견/해결 시 |
| `docs/product_concept.md` | 제품 컨셉, 아키텍처, 기술 스택 | 방향 변경 시 |
