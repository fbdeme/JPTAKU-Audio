# Issues

발견된 이슈, 리스크, 미결정 사항을 기록합니다.

## Open

### ISS-001: 애니메 스타일 Rive 캐릭터 부재
- 립싱크 가능한 애니메 스타일 공개 Rive 캐릭터가 없음
- JcToon 캐릭터로 PoC 진행 후 프로덕션용은 직접 리깅 필요

### ISS-002: A2F-3D 일본어 품질 정밀 평가 필요
- 일본어 오디오에서 BlendShape 추출 자체는 성공 (tsumugi_04.wav 테스트)
- JawOpen, MouthPucker 등 값은 나오지만 발음별 정확도는 미검증
- 실제 Rive 캐릭터에 매핑해서 시각적 품질 확인 필요

### ISS-004: A2F BlendShape 이름이 PascalCase
- A2F 출력: JawOpen, MouthSmileLeft (PascalCase)
- ARKit 표준: jawOpen, mouthSmileLeft (camelCase)
- Rive 매핑 시 케이스 변환 레이어 필요

### ISS-003: ARKit → Rive 매핑 전례 없음
- ARKit 52 BlendShape를 Rive로 퍼펫팅한 공개 사례가 없음
- 우리가 최초 구현, 예상치 못한 문제 가능

## Resolved

### ISS-005: A2F-3D Docker TensorRT 호환성
- CUDA 13.0 환경에서 A2F NIM 컨테이너(1.3) 정상 동작 확인
- TensorRT 엔진 자동 컴파일 성공 (RTX A6000)
