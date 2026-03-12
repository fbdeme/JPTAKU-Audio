#!/usr/bin/env python3
"""
CosyVoice3 모델 다운로드 스크립트 (HuggingFace)
Fun-CosyVoice3-0.5B 모델을 pretrained_models/ 디렉토리에 다운로드합니다.
"""

import os
import sys

def download_model():
    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("[ERROR] huggingface_hub가 설치되지 않았습니다.")
        print("  pip install huggingface_hub 를 먼저 실행하세요.")
        sys.exit(1)

    model_id = "FunAudioLLM/Fun-CosyVoice3-0.5B-2512"
    local_dir = "pretrained_models/Fun-CosyVoice3-0.5B"

    os.makedirs(local_dir, exist_ok=True)

    print(f"[INFO] 다운로드 시작: {model_id}")
    print(f"[INFO] 저장 경로: {local_dir}")
    print("[INFO] (모델 크기가 크기 때문에 시간이 걸릴 수 있습니다...)\n")

    try:
        snapshot_download(
            repo_id=model_id,
            local_dir=local_dir,
            repo_type="model",
        )
        print(f"\n[SUCCESS] 모델 다운로드 완료: {local_dir}")
    except Exception as e:
        print(f"\n[ERROR] 다운로드 실패: {e}")
        print("\n[TIP] HuggingFace 로그인이 필요할 수 있습니다:")
        print("  huggingface-cli login")
        sys.exit(1)


if __name__ == "__main__":
    download_model()
