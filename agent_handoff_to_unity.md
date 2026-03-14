# JPTAKU-Unity 에이전트 작업 지시서 (Handoff Specification)

이 문서는 JPTAKU 프로젝트의 프론트엔드(Unity) 파트를 담당할 다음 에이전트(AI)에게 전달하기 위한 명세서입니다.

## 1. 프로젝트 개요 (Context)
- **목표**: JPTAKU 프로젝트의 실시간 2D 튜터 캐릭터 구현을 위한 Unity 기반 클라이언트 시스템 구축.
- **백엔드 구조 (`JPTAKU-Audio`)**: 
  - TTS: `CosyVoice3`
  - Motion AI: NVIDIA `Audio2Face-3D` (ARKit 52 BlendShape 생성 모델)
  - 특징: 백엔드에서 오디오(`output_voice.wav`)와 프레임별 모션값(ARKit 기반 JSON 데이터 `output_motion.json`)을 생성하여 전달함. 

## 2. JPTAKU-Unity 에이전트의 역할 (Tasks)
다음 에이전트는 `/Users/jeonmingyu/workspace_2026/JPTAKU-Unity` 폴더 내에서 다음 작업들을 수행해야 합니다.

### Task A. 기초 C# 파일 입출력 로직 작성 (PoC 수신부)
- 백엔드(`JPTAKU-Audio`)에서 파일(WAV, JSON) 형태로 넘겨주는 결과물을 Unity에서 읽어들이는 코드를 작성해야 합니다.
- **요구사항**: 
  - `output_voice.wav` 로드 유틸리티 스크립트 작성 (`AudioClip` 생성)
  - `output_motion.json` 로드 및 파싱 클래스 구조체 작성 (`System.Serializable` 활용)
  - 파싱 구조는 다음 JSON 규격을 따릅니다: 
    ```json
    {
      "fps": 30,
      "frames": [
        {"frame": 0, "blendshape_0": 0.0, ..., "blendshape_51": 0.0},
        ...
      ]
    }
    ```

### Task B. BlendShape 매핑 및 재생 컨트롤러 (`BlendShapeSync.cs`) 작성
- 파싱된 JSON 데이터를 타임라인에 맞게 `SkinnedMeshRenderer`에 주입하는 스크립트를 작성합니다.
- **핵심 요구사항**:
  - `AudioSource` 컴포넌트의 `time` 속성과 동기화하여 `Update()` 루프 내에서 처리.
  - JSON의 `fps` 값을 기반으로 현재 오디오 재생 시점에 해당하는 `frame` 배열 인덱스(interpolation 포함)를 찾아 매핑.
  - 캐릭터 오브젝트에 붙은 SkinnedMeshRenderer에 `SetBlendShapeWeight(index, weight 0~100 범위 변환)` 함수를 호출하여 얼굴 애니메이션 반영.

### Task C. (옵션) 임시 구동 Scene 세팅 가이드 준비
- 사용자가 유니티 에디터를 열고 바로 테스트해볼 수 있도록, 필요한 컴포넌트(GameObject, AudioSource 등) 배치 가이드라인과 C# 스크립트 에디터 할당 방법을 Markdown으로 요약해 둡니다.

## 3. 참조 환경 및 특징
- 대상 플랫폼: Mac (Apple Silicon 환경)
- Unity 버전: (가장 최신의 안정화 버전 권장 - 추후 사용자가 설치)
- 캐릭터 표준: VRoid (VRM) 기반의 ARKit 52 BlendShape. (따라서 스크립트 작성 시 BlendShape 이름 문자열을 키(key) 값으로 하드코딩하지 말고, 배열 매핑이 유연하게 가능하도록 Inspector 노출(`public string[] blendshapeNames`) 등을 고려하는 것이 좋습니다.)

## 4. 즉시 실행 (Next Action)
위 내용을 인지하였다면, 곧바로 `Task A`와 `Task B`를 포괄하는 유니티 수신부 C# 뼈대 스크립트(가칭 `Audio2FaceReceiver.cs`) 파일을 작성하기 시작하세요.
