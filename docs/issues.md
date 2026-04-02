# Issues

## Open

### ISS-001: 애니메 스타일 Rive 캐릭터 부재
- 립싱크 가능한 애니메 스타일 공개 Rive 캐릭터가 없음
- JcToon(표정 데모)으로 PoC 성공했지만 립싱크 개별 제어 불가 (Happy/Sad/Surprised/Angry만)
- 프로덕션용은 ARKit BlendShape 1:1 매핑 가능한 캐릭터 직접 리깅 필요

### ISS-002: A2F-3D 일본어 품질 정밀 평가 필요
- 일본어 오디오에서 BlendShape 추출 성공, JawOpen/MouthPucker 등 의미 있는 값 확인
- 발음별 정확도는 프로덕션 캐릭터에서 시각적으로 검증 필요

### ISS-006: 응답 지연 ~5초
- LLM ~1.6초 + TTS + A2F = 순차 ~5초
- TTS를 CosyVoice3 로컬로 전환 완료 — 네트워크 지연 제거됨
- 추가 개선: TTS+A2F 스트리밍 병렬화 필요

### ISS-007: Talking Avatar 캐릭터 매핑 실패
- input 이름이 비표준 (mouth hight, kelopakmata f Slider 등)
- 공개 Rive 캐릭터마다 리깅 구조가 달라 범용 매핑 불가능
- 결론: 프로덕션 캐릭터는 직접 리깅하되 ARKit 이름으로 input 설계

### ISS-008: Rive → Godot 전환 검토
- Rive Editor 유료 + 디자이너 부재로 캐릭터 제작 불가
- Godot Engine으로 전환 시 고려사항:
  - Godot 2D 애니메이션은 뼈대(Skeleton) 기반 — Rive/Live2D의 메쉬 변형과 다른 방식
  - 부드러운 변형이 필요하면 커스텀 셰이더 또는 Inochi2D Godot 바인딩 필요
  - FlutDot(Flutter 내 Godot 임베딩)은 실험적 단계
- A2F ARKit BlendShape → Godot 파라미터 매핑 방법 미검증

### ISS-009: Godot MCP 브릿지에 2D 리깅 도구 없음 → 해결
- ee0pdt/Godot-MCP fork하여 리깅 8개 + 애니메이션 10개 도구 직접 구현
- Skeleton2D/Bone2D/IK + AnimationPlayer/AnimationTree/StateMachine 전체 지원
- E2E 테스트 성공 (Claude Code → MCP → Godot 에디터 실시간 반영)

### ISS-011: CosyVoice3 음성 품질이 레퍼런스에 크게 좌우됨
- 현재 ref_00.wav 하나로 고정 — 음성 결과가 부자연스러울 수 있음
- 레퍼런스 음성 선택/미리듣기 인터페이스 필요
- assets/reference_voice/ 아래 7개 카테고리 40+개 wav 존재하지만 비교/선택 수단 없음

### ISS-010: See-through → 리깅 자동화 갭
- See-through는 레이어 분할만 제공 (리깅 없음, 저자 명시)
- PSD 레이어 → Godot Sprite2D 임포트 → 본 바인딩까지 자동화 스크립트 필요
- 캐릭터별 체형/포즈/비율이 달라 완전 범용 자동 리깅은 매우 어려움
- 단계적 접근: 표준 템플릿 기반 반자동 → AI 보조로 정밀도 개선

## Resolved

### ISS-003: ARKit → Rive 매핑 전례 없음 → PoC로 검증 완료
- JcToon 캐릭터에서 A2F BlendShape → Rive Number Input 매핑 성공
- 공격적 스케일링(x200-500) 필요하지만 동작 확인

### ISS-004: A2F BlendShape PascalCase → 매핑 레이어에서 처리
- BlendShapeMapper에서 PascalCase(JawOpen) 직접 사용

### ISS-005: A2F-3D Docker TensorRT 호환성 → 정상 동작 확인
- CUDA 13.0 + RTX A6000에서 NIM 컨테이너 1.3 정상 실행
