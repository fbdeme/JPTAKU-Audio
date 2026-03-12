#!/usr/bin/env python3
"""
CosyVoice3 Few-Shot 추론 스크립트
Japanese-Eroge-Voice-V2 데이터셋에서 레퍼런스 오디오를 로드하여
CosyVoice3로 Few-shot (Zero-shot) 음성 합성을 수행합니다.

사용법:
    python run_inference.py [options]

옵션:
    --num_samples   추론할 샘플 수 (기본값: 3)
    --output_dir    출력 디렉토리 (기본값: outputs)
    --model_dir     모델 경로 (기본값: pretrained_models/Fun-CosyVoice3-0.5B)
    --target_text   합성할 대상 텍스트 (기본값: 데이터셋 자체 transcription 사용)
    --dataset_split 사용할 데이터셋 split (기본값: train)
    --dataset_offset 데이터셋 시작 offset (기본값: 0)
"""

import argparse
import os
import sys
import numpy as np
import soundfile as sf
import pykakasi

# 가타카나 변환용 객체 초기화
kks = pykakasi.kakasi()

def to_katakana(text: str) -> str:
    """일본어 원문을 가타카나로 변환 (CosyVoice3 일본어 처리를 위함)"""
    if not text:
        return text
    result = kks.convert(text)
    return "".join([item['kana'] for item in result])

# CosyVoice 경로 설정
COSYVOICE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CosyVoice")
sys.path.insert(0, COSYVOICE_DIR)
sys.path.insert(0, os.path.join(COSYVOICE_DIR, "third_party", "Matcha-TTS"))


def load_dataset_sample(dataset_name: str, split: str, offset: int):
    """HuggingFace datasets에서 샘플 스트리밍으로 로드"""
    try:
        import datasets
        from datasets import load_dataset
    except ImportError:
        print("[ERROR] datasets 라이브러리가 설치되지 않았습니다.")
        print("  pip install datasets 를 실행하세요.")
        sys.exit(1)

    print(f"[INFO] 데이터셋 로딩: {dataset_name} (split={split}, streaming=True)")
    print("[INFO] (첫 번째 로드 시 메타데이터 다운로드가 진행됩니다...)\n")

    # decode=False: 오디오를 raw bytes로 로드하여 torchcodec 의존성 제거
    dataset = load_dataset(
        dataset_name,
        split=split,
        streaming=True,
    ).cast_column("audio", datasets.Audio(decode=False))
    # offset 적용
    if offset > 0:
        dataset = dataset.skip(offset)

    return dataset


def cosyvoice_inference(model_dir: str, ref_audio_array: np.ndarray,
                        ref_sample_rate: int, ref_text: str,
                        target_text: str, output_path: str):
    """CosyVoice3 zero-shot 추론 수행"""
    try:
        from cosyvoice.cli.cosyvoice import CosyVoice3
        from cosyvoice.utils.file_utils import load_wav
        import torchaudio
        import torch
        import tempfile
    except ImportError as e:
        print(f"[ERROR] CosyVoice import 실패: {e}")
        print("  CosyVoice 디렉토리가 올바른지 확인하세요.")
        sys.exit(1)

    # 모델 로드 (처음 한 번만)
    if not hasattr(cosyvoice_inference, "_model"):
        print(f"\n[INFO] 모델 로드 중: {model_dir}")
        cosyvoice_inference._model = CosyVoice3(model_dir)
        print("[INFO] 모델 로드 완료!\n")

    model = cosyvoice_inference._model

    # 레퍼런스 오디오를 임시 wav 파일로 저장
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name

    # 데이터셋 오디오가 int16이면 float32로 변환
    if ref_audio_array.dtype == np.int16:
        ref_audio_float = ref_audio_array.astype(np.float32) / 32768.0
    else:
        ref_audio_float = ref_audio_array.astype(np.float32)

    sf.write(tmp_path, ref_audio_float, ref_sample_rate)

    # 자연스러운 발음을 위해 가타카나로 변환
    target_text_kata = to_katakana(target_text)
    ref_text_kata = to_katakana(ref_text)

    print(f"  [가타카나 변환] Text: {target_text_kata[:50]}...")
    print(f"  [가타카나 변환] Ref : {ref_text_kata[:50]}...")

    # Zero-shot 추론 (CosyVoice3 API: prompt_wav에 파일 경로 전달, prompt_text 끝에 <|endofprompt|> 추가)
    output_list = list(model.inference_zero_shot(
        tts_text=target_text_kata,
        prompt_text=ref_text_kata + "<|endofprompt|>",
        prompt_wav=tmp_path,
        stream=False,
    ))

    # 임시 파일 삭제
    os.unlink(tmp_path)

    if not output_list:
        print("  [WARNING] 추론 결과가 없습니다.")
        return

    # 결과 오디오 저장 (model.sample_rate = 24000)
    audio_tensor = output_list[0]["tts_speech"]
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    torchaudio.save(output_path, audio_tensor, model.sample_rate)
    print(f"  [SUCCESS] 저장 완료: {output_path}\n")


def main():
    parser = argparse.ArgumentParser(
        description="CosyVoice3 Few-Shot Inference with Japanese-Eroge-Voice-V2"
    )
    parser.add_argument("--num_samples", type=int, default=3,
                        help="추론할 샘플 수 (기본값: 3)")
    parser.add_argument("--output_dir", type=str, default="outputs",
                        help="출력 디렉토리 (기본값: outputs)")
    parser.add_argument("--model_dir", type=str,
                        default="pretrained_models/Fun-CosyVoice3-0.5B",
                        help="모델 경로")
    parser.add_argument("--target_text", type=str, default=None,
                        help="합성할 텍스트 (미지정시 데이터셋 텍스트 사용)")
    parser.add_argument("--dataset_split", type=str, default="train",
                        help="데이터셋 split (기본값: train)")
    parser.add_argument("--dataset_offset", type=int, default=0,
                        help="데이터셋 시작 offset (기본값: 0)")
    args = parser.parse_args()

    # 모델 경로 확인
    if not os.path.exists(args.model_dir):
        print(f"[ERROR] 모델 디렉토리가 존재하지 않습니다: {args.model_dir}")
        print("  먼저 모델을 다운로드하세요:")
        print("  python download_model.py")
        sys.exit(1)

    os.makedirs(args.output_dir, exist_ok=True)

    # 데이터셋 로드
    dataset = load_dataset_sample(
        "NandemoGHS/Japanese-Eroge-Voice-V2",
        split=args.dataset_split,
        offset=args.dataset_offset,
    )

    print(f"[INFO] {args.num_samples}개 샘플에 대해 Few-shot 추론을 시작합니다.\n")
    print("=" * 60)

    processed = 0
    for i, sample in enumerate(dataset):
        if processed >= args.num_samples:
            break

        try:
            # 오디오 데이터 추출 (decode=False 모드: bytes or path로 옴)
            import io
            import soundfile as sf

            audio_data = sample["audio"]
            ref_text = sample["text"]
            text_source = sample.get("text_source", "unknown")

            # decode=False 시 audio_data는 {'bytes': ..., 'path': ...} dict
            audio_bytes = audio_data.get("bytes")
            audio_path = audio_data.get("path")

            if audio_bytes is not None and len(audio_bytes) > 0:
                buf = io.BytesIO(audio_bytes)
                ref_audio_array, ref_sample_rate = sf.read(buf)
            elif audio_path is not None and os.path.exists(audio_path):
                ref_audio_array, ref_sample_rate = sf.read(audio_path)
            else:
                print(f"[SKIP] 샘플 {i}: 오디오 데이터 없음")
                continue

            ref_audio_array = np.array(ref_audio_array, dtype=np.float32)
            # 스테레오면 mono로 변환
            if ref_audio_array.ndim > 1:
                ref_audio_array = ref_audio_array.mean(axis=1)

            # 레퍼런스 오디오가 너무 짧거나 길면 스킵
            duration = len(ref_audio_array) / ref_sample_rate
            if duration < 2.0 or duration > 30.0:
                print(f"[SKIP] 샘플 {i}: 오디오 길이 {duration:.1f}초 (범위 2~30초)")
                continue

            # 합성 대상 텍스트 결정
            target_text = args.target_text if args.target_text else ref_text

            print(f"\n[샘플 {processed+1}/{args.num_samples}] (데이터셋 index: {i})")
            print(f"  - 오디오 길이: {duration:.2f}초 ({ref_sample_rate}Hz)")
            print(f"  - Transcription: {ref_text[:80]}...")
            print(f"  - text_source: {text_source}")

            output_filename = f"sample_{processed+1:03d}_idx{i}.wav"
            output_path = os.path.join(args.output_dir, output_filename)

            cosyvoice_inference(
                model_dir=args.model_dir,
                ref_audio_array=ref_audio_array,
                ref_sample_rate=ref_sample_rate,
                ref_text=ref_text,
                target_text=target_text,
                output_path=output_path,
            )

            processed += 1

        except Exception as e:
            print(f"[WARNING] 샘플 {i} 처리 중 오류: {e}")
            continue

    print("=" * 60)
    print(f"\n[DONE] 총 {processed}개 샘플 추론 완료!")
    print(f"[DONE] 출력 파일 위치: {os.path.abspath(args.output_dir)}/")
    if processed > 0:
        print("\n생성된 파일 목록:")
        for f in sorted(os.listdir(args.output_dir)):
            if f.endswith(".wav"):
                fpath = os.path.join(args.output_dir, f)
                print(f"  - {f} ({os.path.getsize(fpath)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
