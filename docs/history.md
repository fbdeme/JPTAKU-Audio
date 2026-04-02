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

## 2026-04-02: 캐릭터 자동 생성 파이프라인 R&D 시작

- **프로덕션 캐릭터 부재 문제** — 디자이너 없이 캐릭터를 만들 방법 필요
- Rive Editor 유료 + 수작업 → 오픈소스 대안 조사

### 기술 조사 결과

**오픈소스 2D 에디터 비교:**
- Godot Engine (MIT) — 유일하게 현실적인 후보
  - AnimationTree 상태 머신 내장 (Rive State Machine과 동일 역할)
  - MCP 브릿지 다수 존재 (ee0pdt/Godot-MCP 518 stars, GodotIQ, Godot MCP Pro 등)
  - Web(Wasm) 내보내기 프로덕션급, Flutter 임베딩(FlutDot) 가능
  - AI 에이전트(Claude Code) 연동 가능 — MCP 프로토콜로 에디터 제어
- Inochi2D (BSD-2) — Live2D 대안, 메쉬 변형 방식이지만 Flutter/Web 런타임 없음
- Blender (GPL) — Python API 강력하지만 런타임 없음 (제작 도구 전용)
- Synfig, DragonBones, OpenToonz — 상태 머신 없거나 에디터 비공개

**See-through (shitagaki-lab/see-through, SIGGRAPH 2026):**
- Apache-2.0, 일러스트 → 최대 24개 의미론적 레이어 PSD 자동 분할
- SDXL 기반, RTX 3090/4090에서 테스트됨, 이미지당 ~84초
- 가려진 부분 인페인팅 자동 처리 (LaMa)
- 레이어 분할까지만 — 리깅 자동화는 아직 세상에 없음

**Godot MCP 브릿지 비교:**
- ee0pdt/Godot-MCP (MIT, 518 stars) — 19개 도구, 확장 구조 좋음
- GodotIQ (MIT+$19 Pro) — 36개 도구, 애니메이션 읽기만
- Godot MCP Pro ($5) — 163개 도구, AnimationTree 생성 가능하지만 유료
- 결론: ee0pdt/Godot-MCP fork하여 2D 리깅 특화 도구 추가 방향

### 결정 사항

- **방향**: Claude Code + Godot MCP로 "바이브 코딩" 스타일 캐릭터 리깅
  - Claude Code가 MCP 프로토콜로 Godot 에디터를 직접 제어
  - 사용자가 에디터 보면서 자연어로 지시, AI가 실행
- **파이프라인**: 일러스트 → See-through (레이어 분할) → Godot (AI 협업 리깅) → Web Export
- **MCP 서버**: ee0pdt/Godot-MCP fork → Skeleton2D/Bone2D, Animation, AnimationTree 도구 확장

### 구현 완료

**Godot MCP 서버 확장 (18개 새 도구):**
- ee0pdt/Godot-MCP (MIT, 518 stars) 클론 후 2D 리깅 특화 도구 추가
- **리깅 도구 8개**: create_skeleton2d, add_bone2d, create_bone_chain, get_skeleton_info, bind_polygon2d_to_skeleton, set_bone2d_rest, create_sprite_with_texture, setup_ik_chain
- **애니메이션 도구 10개**: create_animation_player, create_animation, add_animation_track, set_animation_keyframe, list_animations, get_animation_info, create_animation_tree, add_state_machine_state, add_state_machine_transition, set_blend_tree_parameter
- GDScript 커맨드 프로세서: rigging_commands.gd, animation_commands.gd
- TypeScript MCP 도구 정의: rigging_tools.ts, animation_tools.ts

**noVNC 기반 Godot 에디터 웹 접속 구축:**
- Xvfb :99 (가상 디스플레이 1920x1080) + x11vnc + noVNC(:6080)
- Godot 4.4.1 에디터가 Vulkan + RTX A6000 GPU 가속으로 동작
- 브라우저에서 http://localhost:6080/vnc.html 로 에디터 접속

**E2E 테스트 성공:**
- Claude Code → MCP(WS:9080) → Godot Editor 명령 전달 검증
- create_skeleton2d → add_bone2d → create_bone_chain → get_skeleton_info 전체 흐름 성공
- Godot 에디터에서 CharacterSkeleton > Hip > Spine_0/1/2 노드 실시간 생성 확인

## 2026-04-02: TTS 로컬화 + 레거시 정리

- **TTS 교체**: OpenAI TTS(nova) → CosyVoice3 few-shot (로컬 모델)
  - chat_server.py에서 CosyVoice3 inference_zero_shot() 직접 호출
  - 가타카나 변환(pykakasi) 적용, ref_00.wav 레퍼런스 음성 사용
  - 외부 API 의존성 제거 (TTS 부분), GPU 로컬 추론
- **레거시 파일 대량 정리**:
  - 삭제: DyStream 서브모듈, pipeline/ 전체 (THA4+LAM+GPT-SoVITS+Gradio)
  - 삭제: poc_*.py 4개, setup scripts, requirements.txt, agent_handoff_to_unity.md
  - pyproject.toml 의존성 정리 (GPT-SoVITS, LAM, THA4, Gradio 등 제거)
