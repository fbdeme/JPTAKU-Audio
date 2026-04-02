# Product Concept

## 비전
인터랙티브 일본어 튜터 컴패니언 앱. 애니메 스타일 캐릭터 "凛(Rin)"이 음성과 표정으로 일본어를 가르쳐주는 모바일 앱.

## 아키텍처 (PoC 검증 완료)

```
User Input (text)
    ↓
[GPT-4o-mini] — 일본어 튜터 응답 생성 (~1.6s)
    ↓
[CosyVoice3] — 음성 합성 (few-shot, 로컬 GPU)
    ↓
[NVIDIA Audio2Face-3D] — 오디오 → ARKit 55 BlendShapes (~2s, Docker 로컬)
    ↓ (WebSocket, 30fps)
[Flutter + Rive] — 2D 캐릭터 표정 구동 + 음성 재생
```

## 기술 스택

| 레이어 | PoC | 프로덕션 예정 |
|--------|-----|-------------|
| LLM | GPT-4o-mini | GPT-4o-mini |
| TTS | CosyVoice3 few-shot (로컬) | CosyVoice3 (레퍼런스 음성 교체로 커스텀) |
| Expression | NVIDIA A2F-3D Docker | NVIDIA A2F-3D |
| Backend | aiohttp + websockets (Python) | 동일 |
| Frontend | Flutter Web (PoC) | Flutter Mobile (Android/iOS) |
| Rendering | Rive (JcToon 데모 캐릭터) | Rive (커스텀 애니메 캐릭터) |

## 캐릭터
- **이름**: 凛 (Rin)
- **성격**: 차분하고 다정한 언니 타입
- **스타일**: 애니메 2D (Rive로 렌더링)
- **음성**: CosyVoice3 few-shot (ref_00.wav 레퍼런스)

## PoC 결과 요약 (2026-04-02)
- **E2E 파이프라인 동작 확인**: 텍스트 → LLM → TTS → A2F → WS → Rive 표정 변화
- **A2F-3D 일본어 지원**: JawOpen 0-0.8, MouthPucker 0-0.5 등 세밀한 값 추출
- **핵심 과제**: 프로덕션용 Rive 캐릭터 리깅 (ARKit BlendShape 1:1 매핑)

## 캐릭터 자동 생성 파이프라인 (R&D)

디자이너 없이 AI 에이전트(Claude Code)와 협업하여 캐릭터를 제작하는 시스템.

```
[일러스트] → [See-through] → [Godot + Claude Code MCP] → [Web Export]
  AI 생성       24개 레이어       AI 협업 리깅            Wasm 배포
  or 업로드     PSD 자동 분할     자연어로 지시
```

| 레이어 | 도구 | 역할 |
|--------|------|------|
| 레이어 분할 | See-through (SIGGRAPH 2026, Apache-2.0) | 일러스트 → 24개 의미론적 레이어 PSD |
| 리깅 에디터 | Godot Engine (MIT) | Skeleton2D, AnimationTree, Web Export |
| AI 에이전트 | Claude Code + Godot MCP | 에디터를 MCP로 제어, 사용자와 협업 |
| MCP 서버 | ee0pdt/Godot-MCP fork (MIT) | 2D 리깅 특화 도구 확장 |

## 레거시 (폐기된 접근법)
- Unity 프론트엔드 → Flutter로 전환
- THA4 렌더링 → Rive로 전환
- LAM-Audio2Expression → NVIDIA A2F-3D로 전환
- Live2D → Flutter 지원 부족으로 Rive 선택
- DyStream, SkyReels-A1 → 실사 얼굴 전용, 애니메 불가
- CosyVoice3 초기 시도 → 중국어 프론트엔드 문제 있었으나 가타카나 변환으로 해결
- OpenAI TTS → 로컬 CosyVoice3로 교체 (외부 API 의존성 제거)
- GPT-SoVITS → CosyVoice3로 통합 (별도 API 서버 불필요)
