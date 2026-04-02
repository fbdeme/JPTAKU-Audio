# Product Concept

## 비전
인터랙티브 일본어 튜터 컴패니언 앱. 애니메 스타일 캐릭터 "凛(Rin)"이 음성과 표정으로 일본어를 가르쳐주는 모바일 앱.

## 아키텍처 (PoC 검증 완료)

```
User Input (text)
    ↓
[GPT-4o-mini] — 일본어 튜터 응답 생성 (~1.6s)
    ↓
[OpenAI TTS] — 음성 합성 (~1.7s, 추후 GPT-SoVITS로 교체)
    ↓
[NVIDIA Audio2Face-3D] — 오디오 → ARKit 55 BlendShapes (~2s, Docker 로컬)
    ↓ (WebSocket, 30fps)
[Flutter + Rive] — 2D 캐릭터 표정 구동 + 음성 재생
```

## 기술 스택

| 레이어 | PoC | 프로덕션 예정 |
|--------|-----|-------------|
| LLM | GPT-4o-mini | GPT-4o-mini |
| TTS | OpenAI TTS (nova) | GPT-SoVITS (로컬, 보이스 클로닝) |
| Expression | NVIDIA A2F-3D Docker | NVIDIA A2F-3D |
| Backend | aiohttp + websockets (Python) | 동일 |
| Frontend | Flutter Web (PoC) | Flutter Mobile (Android/iOS) |
| Rendering | Rive (JcToon 데모 캐릭터) | Rive (커스텀 애니메 캐릭터) |

## 캐릭터
- **이름**: 凛 (Rin)
- **성격**: 차분하고 다정한 언니 타입
- **스타일**: 애니메 2D (Rive로 렌더링)
- **음성**: OpenAI TTS nova (PoC), VOICEVOX Kasukabe Tsumugi 예정

## PoC 결과 요약 (2026-04-02)
- **E2E 파이프라인 동작 확인**: 텍스트 → LLM → TTS → A2F → WS → Rive 표정 변화
- **A2F-3D 일본어 지원**: JawOpen 0-0.8, MouthPucker 0-0.5 등 세밀한 값 추출
- **핵심 과제**: 프로덕션용 Rive 캐릭터 리깅 (ARKit BlendShape 1:1 매핑)

## 레거시 (폐기된 접근법)
- Unity 프론트엔드 → Flutter로 전환
- THA4 렌더링 → Rive로 전환
- LAM-Audio2Expression → NVIDIA A2F-3D로 전환
- Live2D → Flutter 지원 부족으로 Rive 선택
- DyStream, SkyReels-A1 → 실사 얼굴 전용, 애니메 불가
- CosyVoice3 → 중국어 프론트엔드가 일본어 발음 깨뜨림
