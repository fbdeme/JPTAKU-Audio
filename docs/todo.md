# TODO

## In Progress

- [ ] See-through 로컬 설치 + 테스트
- [ ] PSD 임포트 + BlendShape 매핑 MCP 도구 추가

## Upcoming

- [ ] See-through PSD → Godot 자동 임포트 스크립트
- [ ] A2F ARKit BlendShape → Godot AnimationTree 파라미터 매핑
- [ ] Godot Web Export(Wasm) → 기존 파이프라인 연동
- [ ] GPT-SoVITS TTS로 교체 (OpenAI TTS → 로컬, 보이스 클로닝)
- [ ] 오디오 재생 + 표정 타이밍 정밀 싱크
- [ ] 응답 지연 최적화 (현재 ~5초 → 목표 1-2초)
- [ ] Flutter 모바일 빌드 (Android/iOS)
- [ ] Flutter WebSocket 연동 안정화 (현재 web_socket_channel 사용)

## Done

- [x] Rive 기술 조사
- [x] LAM vs A2F-3D 비교 → A2F-3D 선택
- [x] 공개 Rive 캐릭터 조사
- [x] Flutter 프로젝트 생성 + Rive 패키지 설정 (app/)
- [x] JcToon .riv + Talking Avatar .riv 다운로드
- [x] Number Input 슬라이더 UI 구현
- [x] A2F-3D Docker 로컬 실행 (nvcr.io/nim/nvidia/audio2face-3d:1.3)
- [x] 일본어 오디오 → ARKit 55 BlendShape 추출 성공
- [x] Python WebSocket 서버 — BlendShape 30fps 스트리밍
- [x] 채팅 서버 (LLM + TTS + A2F + WS 통합)
- [x] Flutter 채팅 UI + 음성 재생 + Rive 표정 구동
- [x] **E2E PoC 성공: 텍스트 → LLM → TTS → A2F → WS → Flutter Rive 표정 변화**
- [x] Godot MCP 서버 구축 (ee0pdt/Godot-MCP fork + 18개 2D 리깅/애니메이션 도구)
- [x] Godot 4.4.1 설치 + noVNC 웹 에디터 접속 환경 구축
- [x] MCP 연동 E2E 테스트 (Claude Code → MCP → Godot 에디터 실시간 반영)
