#!/usr/bin/env python3
"""
JPTAKU - CosyVoice3 + DyStream PoC Pipeline
단일 스크립트로 텍스트 입력 -> 음성 합성(CosyVoice3) -> 비디오 렌더링(DyStream)을 수행합니다.

사용법:
    python poc_pipeline.py \
        --text "先生、そんなに見つめられると恥ずかしいです。" \
        --ref_audio "assets/reference_voice.wav" \
        --ref_text "参考用テキスト" \
        --image "assets/character.png" \
        --output "output_avatar.mp4"
"""

import argparse
import os
import sys
import subprocess
import tempfile
import numpy as np
import soundfile as sf

# 1. CosyVoice 추론 함수 (기존 run_inference.py 로직 캡슐화)
def generate_audio(text: str, ref_audio_path: str, ref_text: str, output_wav_path: str):
    print(f"\n[Phase 1] CosyVoice3 음성 합성 시작...")
    print(f"  - Target Text: {text}")
    print(f"  - Ref Audio: {ref_audio_path}")
    
    # CosyVoice 경로 설정 및 임포트
    COSYVOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CosyVoice")
    sys.path.insert(0, COSYVOICE_DIR)
    sys.path.insert(0, os.path.join(COSYVOICE_DIR, "third_party", "Matcha-TTS"))
    
    try:
        from cosyvoice.cli.cosyvoice import CosyVoice3
        import torchaudio
        import pykakasi
    except ImportError as e:
        print(f"[ERROR] 파이썬 패키지 로드 실패: {e}")
        sys.exit(1)

    # 가타카나 변환기
    kks = pykakasi.kakasi()
    def to_katakana(t: str) -> str:
        if not t: return t
        return "".join([item['kana'] for item in kks.convert(t)])

    model_dir = "pretrained_models/Fun-CosyVoice3-0.5B"
    model = CosyVoice3(model_dir)
    
    # 레퍼런스 및 타겟 텍스트 변환
    target_text_kata = to_katakana(text)
    ref_text_kata = to_katakana(ref_text)
    
    # Zero-shot 추론
    output_list = list(model.inference_zero_shot(
        tts_text=target_text_kata,
        prompt_text=ref_text_kata + "<|endofprompt|>",
        prompt_wav=ref_audio_path,
        stream=False,
    ))
    
    if not output_list:
        raise RuntimeError("음성 합성 결과가 없습니다.")
        
    audio_tensor = output_list[0]["tts_speech"]
    os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
    torchaudio.save(output_wav_path, audio_tensor, model.sample_rate)
    print(f"  [SUCCESS] 음성 합성 완료: {output_wav_path}")


# 2. DyStream 렌더링 호출 함수
def generate_video(audio_path: str, image_path: str, output_mp4_path: str):
    print(f"\n[Phase 2] DyStream 비디오 렌더링 시작...")
    print(f"  - Input Audio: {audio_path}")
    print(f"  - Character Image: {image_path}")
    
    # TODO: 사용자의 DyStream 설치 경로에 맞게 수정 필요
    DYSTREAM_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DyStream")
    
    if not os.path.exists(DYSTREAM_DIR):
        print(f"[WARNING] DyStream 폴더를 찾을 수 없습니다: {DYSTREAM_DIR}")
        print("  현재는 임시로 ffmpeg를 활용해 오디오와 정지 이미지를 결합한 mock 비디오를 만듭니다.")
        print("  실제 DyStream 환경이 세팅되면 이 부분의 subprocess 구문을 DyStream 실행 명령어로 교체하세요.")
        
        # MOCK 구현: ffmpeg 로 정지 이미지 + 오디오 결합 (테스트용)
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-i", audio_path, "-c:v", "libx264", "-tune", "stillimage",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-shortest", output_mp4_path
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"  [MOCK SUCCESS] 테스트 비디오 생성 완료: {output_mp4_path}")
        return

    # 실제 DyStream 오프라인 추론 명령어 (DyStream의 CLI 구조에 따라 변경)
    # 예시: python inference.py --source_image <image> --driving_audio <audio> --output <output>
    cmd = [
        "python", os.path.join(DYSTREAM_DIR, "inference.py"),  # 스크립트명은 실제에 맞게 수정
        "--source_image", image_path,
        "--driving_audio", audio_path,
        "--output", output_mp4_path
    ]
    
    try:
        # DyStream 가상환경이 별도로 있다면 해당 파이썬 실행 파이를 지정해야 할 수 있습니다.
        subprocess.run(cmd, cwd=DYSTREAM_DIR, check=True)
        print(f"  [SUCCESS] 애니메이션 비디오 렌더링 완료: {output_mp4_path}")
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] DyStream 렌더링 실패: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="CosyVoice3 + DyStream PoC Pipeline")
    parser.add_argument("--text", required=True, help="합성할 대사 텍스트")
    parser.add_argument("--ref_audio", required=True, help="CosyVoice 레퍼런스 음성 파일 (.wav)")
    parser.add_argument("--ref_text", required=True, help="레퍼런스 음성의 대본")
    parser.add_argument("--image", required=True, help="렌더링할 캐릭터 원본 이미지 (.png/.jpg)")
    parser.add_argument("--output", default="output_avatar.mp4", help="결과물 비디오 경로")
    args = parser.parse_args()

    # 파일 존재 여부 확인
    if not os.path.exists(args.ref_audio):
        print(f"[ERROR] 레퍼런스 오디오 파일이 없습니다: {args.ref_audio}")
        return
    if not os.path.exists(args.image):
        print(f"[ERROR] 캐릭터 이미지 파일이 없습니다: {args.image}")
        return

    # 파이프라인 시작
    print("="*60)
    print(" JPTAKU Avatar PoC Pipeline Started ")
    print("="*60)

    # 임시 WAV 파일 경로
    tmp_wav_path = os.path.join(tempfile.gettempdir(), "poc_temp_audio.wav")

    try:
        # Phase 1: Text to Audio
        generate_audio(args.text, args.ref_audio, args.ref_text, tmp_wav_path)
        
        # Phase 2: Audio + Image to Video
        generate_video(tmp_wav_path, args.image, args.output)
        
    except Exception as e:
        print(f"\n[FATAL ERROR] 파이프라인 실행 중 오류 발생: {e}")
    finally:
        # 정리
        if os.path.exists(tmp_wav_path):
            os.remove(tmp_wav_path)
            
    print("\n" + "="*60)
    print(f" [DONE] 파이프라인 종료. 최종 산출물: {args.output}")
    print("="*60)


if __name__ == "__main__":
    main()
