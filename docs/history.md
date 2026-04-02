# History

프로젝트 진행 이력을 시간순으로 기록합니다.

## 2026-03-12 ~ 2026-03-16: 초기 파이프라인 구축

- CosyVoice3 기반 TTS PoC 시작 (macOS venv)
- vast.ai GPU 서버 셋업 스크립트 작성
- NVIDIA Audio2Face PoC 스크립트 작성
- Unity 핸드오프 문서 작성 (JPTAKU-Unity)
- DyStream PoC → 애니메 캐릭터에서 스타일 깨짐 확인
- 기술 스택 확정: CosyVoice → GPT-SoVITS, DyStream → LAM + THA4
- Gradio 기반 인터랙티브 튜터 앱 완성 (pipeline/app_tutor.py)
- 레퍼런스 보이스 대량 추가, 환경 재현 스크립트 작성

## 2026-04-01: 방향 전환 — 컴패니언 앱 + PoC 파이프라인 완성

- 이미지 기반 캐릭터 조절 → 컴패니언 앱으로 전환
- 프론트엔드: Unity → Flutter, 렌더링: THA4 → Rive, 모션: LAM → A2F-3D
- Rive 조사, LAM vs A2F-3D 비교 → A2F-3D 선택
- Flutter 프로젝트 생성 (app/), Rive 0.14.4 패키지 연동
- A2F-3D Docker 컨테이너 설정 (nvcr.io/nim/nvidia/audio2face-3d:1.3)
- 일본어 오디오 → ARKit 55 BlendShape 추출 성공 (156프레임/5.2초)
- Python WebSocket 서버 구현 (scripts/a2f_poc/ws_server.py)
- Flutter WebSocket 클라이언트 + BlendShapeMapper 구현
- 첫 커밋 & 푸시 (0599181)

## 2026-04-02: 채팅 파이프라인 완성 + E2E PoC 성공

- 채팅 서버 구현 (scripts/a2f_poc/chat_server.py)
  - aiohttp 기반 HTTP + websockets 라이브러리 WS (별도 포트)
  - 텍스��� → GPT-4o-mini → OpenAI TTS → A2F-3D → WS 스트리밍
- Flutter 채팅 UI 구현 (채팅 버블, 음성 재생, Replay 기능)
- BlendShapeMapper: A2F PascalCase → JcToon 표정(Happy/Sad/Surprised/Angry) 매핑
  - A2F 값이 0-0.7 범위라 공격적 스케일링 적용 (x200~500)
- Talking Avatar 캐릭터 시도 → input 이름 불일치로 표정 반영 실패
  - Talking Avatar inputs: mouth hight, mouth witdh, kelopakmata f Slider 등
  - 매핑 추가했으나 캐릭터 자체 리깅 한계로 효과 미미
- JcToon 캐릭터로 복원 → **채팅 + 음성 + 표정 ��화 E2E PoC 성공**
- 교훈: 공개 Rive 캐릭터는 리깅 구조가 다 달라서 매핑 커스텀 필요
  - 프로덕션에서는 ARKit BlendShape 1:1 매핑 가능한 캐릭터 직접 리깅 필요
- JS Web PoC도 별도 작성 (app/web_poc/) — 브라우저 WS 동작 검증용
