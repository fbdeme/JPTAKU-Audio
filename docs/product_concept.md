# Product Concept

## 비전
인터랙티브 일본어 튜터 컴패니언 앱. 애니메 스타일 캐릭터 "凛(Rin)"이 음성과 표정으로 일본어를 가르쳐주는 모바일 앱.

## 아키텍처

```
User Input (text/voice)
    ↓
[GPT-4o-mini] — 일본어 튜터 응답 생성
    ↓
[GPT-SoVITS] — TTS (VOICEVOX Kasukabe Tsumugi 보이스 클로닝)
    ↓
[NVIDIA Audio2Face-3D] — 오디오 → ARKit 52 BlendShapes + 감정 감지
    ↓ (WebSocket/gRPC)
[Flutter + Rive] — 2D 애니메 캐릭터 실시간 렌더링
```

## 기술 스택

| 레이어 | 기술 | 역할 |
|--------|------|------|
| LLM | GPT-4o-mini | 일본어 튜터 페르소나 |
| TTS | GPT-SoVITS v2ProPlus | 음성 합성, 제로샷 보이스 클로닝 |
| Expression | NVIDIA Audio2Face-3D | 오디오 → 표정 (ARKit 52 BlendShapes) |
| Frontend | Flutter + Rive | 크로스 플랫폼 모바일 앱 + 2D 애니메이션 |

## 캐릭터
- **이름**: 凛 (Rin)
- **성격**: 차분하고 다정한 언니 타입
- **스타일**: 애니메 2D
- **음성**: VOICEVOX Kasukabe Tsumugi 기반

## 레거시 (폐기된 접근법)
- Unity 프론트엔드 → Flutter로 전환
- THA4 렌더링 → Rive로 전환
- LAM-Audio2Expression → NVIDIA A2F-3D로 전환
- Live2D → Flutter 지원 부족으로 Rive 선택
- DyStream, SkyReels-A1 → 실사 얼굴 전용, 애니메 불가
- CosyVoice3 → 중국어 프론트엔드가 일본어 발음 깨뜨림
