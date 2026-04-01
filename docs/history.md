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

## 2026-04-01: 방향 전환 — 컴패니언 앱

- 이미지 기반 캐릭터 조절 → 컴패니언 앱으로 전환
- 프론트엔드: Unity → Flutter
- 렌더링: THA4 → Rive (Live2D는 Flutter 지원 부족)
- 모션 엔진: LAM → NVIDIA Audio2Face-3D로 변경 결정
  - A2F가 감정 감지, 립싱크 정확도, 일본어 지원, 성능 모두 우위
- Rive 조사 완료: Additive Blend State + Number Input으로 퍼펫팅 가능 확인
- 공개 Rive 캐릭터 조사: JcToon Facial Expression Demo를 PoC 타겟으로 선정
- PoC 작업 시작: Flutter + Rive + A2F-3D 파이프라인
- Flutter 3.32.0 설치, `app/` 프로젝트 생성, rive 0.14.4 패키지 추가
- JcToon Facial Expression + Talking Avatar .riv 파일 다운로드
- Rive v0.14 API 파악: RiveWidgetController + stateMachine.number() 패턴
- 슬라이더 UI로 Rive 캐릭터 표정 수동 제어 앱 구현 (web 빌드 성공)
- A2F-3D Docker 컨테이너 설정 (nvcr.io/nim/nvidia/audio2face-3d:1.3)
  - NGC API Key로 인증, claire 모델, TensorRT 엔진 자동 컴파일
  - gRPC 서비스 localhost:52000
- **일본어 오디오(tsumugi_04.wav) → ARKit 55 BlendShape 추출 성공**
  - 5.19초 오디오에서 156프레임(30fps) 생성
  - JawOpen, MouthPucker, BrowOuterUp 등 의미 있는 값 확인
  - scripts/a2f_poc/main.py — gRPC 클라이언트 완성
