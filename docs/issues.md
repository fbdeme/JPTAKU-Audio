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
- LLM ~1.6초 + TTS ~1.7초 + A2F ~2초 = 순차 ~5초
- 개선: TTS+A2F 스트리밍 병렬화, 로컬 TTS(GPT-SoVITS) 전환 시 ~1-2초 가능

### ISS-007: Talking Avatar 캐릭터 매핑 실패
- input 이름이 비표준 (mouth hight, kelopakmata f Slider 등)
- 공개 Rive 캐릭터마다 리깅 구조가 달라 범용 매핑 불가능
- 결론: 프로덕션 캐릭터는 직접 리깅하되 ARKit 이름으로 input 설계

## Resolved

### ISS-003: ARKit → Rive 매핑 전례 없음 → PoC로 검증 완료
- JcToon 캐릭터에서 A2F BlendShape → Rive Number Input 매핑 성공
- 공격적 스케일링(x200-500) 필요하지만 동작 확인

### ISS-004: A2F BlendShape PascalCase → 매핑 레이어에서 처리
- BlendShapeMapper에서 PascalCase(JawOpen) 직접 사용

### ISS-005: A2F-3D Docker TensorRT 호환성 → 정상 동작 확인
- CUDA 13.0 + RTX A6000에서 NIM 컨테이너 1.3 정상 실행
