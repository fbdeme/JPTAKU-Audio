#!/usr/bin/env python3
"""
JPTAKU Full Pipeline:
  Text → CosyVoice3 (TTS) → LAM-Audio2Expression (ARKit 52) → THA4 → Video

Usage:
  python poc_full_pipeline.py \
    --text "先生、そんなに見つめられると恥ずかしいです。" \
    --character data/character_models/lambda_00/character.png \
    --output outputs/full_pipeline.mp4
"""
import os
import sys
import time
import json
import argparse
import tempfile
import numpy as np
import torch

# Add paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
LAM_DIR = os.path.join(PROJECT_ROOT, "LAM_Audio2Expression")
sys.path.insert(0, LAM_DIR)

# wx stub for THA4 converter
import types
_wx = types.ModuleType('wx')
for _a in ['Panel','BoxSizer','StaticText','VERTICAL','HORIZONTAL','ALL','EXPAND',
           'Slider','SL_HORIZONTAL','EVT_SLIDER','CheckBox','EVT_CHECKBOX',
           'Choice','EVT_CHOICE','Event','CommandEvent','ID_ANY','Button','EVT_BUTTON']:
    setattr(_wx, _a, type(_a, (), {'__init__': lambda s, *a, **k: None}))
_wx.VERTICAL=0;_wx.HORIZONTAL=1;_wx.ALL=0;_wx.EXPAND=0;_wx.SL_HORIZONTAL=0
_wx.EVT_SLIDER=None;_wx.EVT_CHECKBOX=None;_wx.EVT_CHOICE=None;_wx.EVT_BUTTON=None;_wx.ID_ANY=-1
sys.modules['wx'] = _wx

# Load .env
from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))


# ─── Step 1: CosyVoice3 TTS ─────────────────────────────────────────────────

def run_cosyvoice_tts(text, ref_audio_path, ref_text, output_wav_path):
    """Generate speech from text using CosyVoice3 zero-shot TTS."""
    print(f"[1/4] CosyVoice3 TTS...")
    print(f"  Text: {text}")

    COSYVOICE_DIR = os.path.join(PROJECT_ROOT, "CosyVoice")
    matcha_dir = os.path.join(COSYVOICE_DIR, "third_party", "Matcha-TTS")
    if COSYVOICE_DIR not in sys.path:
        sys.path.insert(0, COSYVOICE_DIR)
    if matcha_dir not in sys.path:
        sys.path.insert(0, matcha_dir)

    from cosyvoice.cli.cosyvoice import CosyVoice3
    import torchaudio

    model_dir = os.path.join(PROJECT_ROOT, "pretrained_models", "Fun-CosyVoice3-0.5B")
    model = CosyVoice3(model_dir)

    # Use instruct2 for best Japanese pronunciation quality
    # instruct_text guides the speaking style, prompt_wav provides voice timbre
    output_list = list(model.inference_instruct2(
        tts_text=text + "<|endofprompt|>",
        instruct_text="かわいい日本の女の子の声で話して。",
        prompt_wav=ref_audio_path,
        stream=False,
    ))

    if not output_list:
        raise RuntimeError("TTS output is empty")

    audio_tensor = output_list[0]["tts_speech"]
    os.makedirs(os.path.dirname(os.path.abspath(output_wav_path)), exist_ok=True)
    torchaudio.save(output_wav_path, audio_tensor, model.sample_rate)

    sample_rate = model.sample_rate
    duration = audio_tensor.shape[-1] / sample_rate
    print(f"  Generated: {output_wav_path} ({duration:.1f}s, {sample_rate}Hz)")

    # Free GPU memory
    del model
    import gc; gc.collect()
    torch.cuda.empty_cache()

    return output_wav_path, sample_rate


# ─── Step 2: LAM Audio2Expression ────────────────────────────────────────────

def run_lam_inference(audio_path):
    """Run LAM and return per-frame ARKit 52 blendshape dicts."""
    print(f"[2/4] LAM Audio2Expression...")

    orig_cwd = os.getcwd()
    os.chdir(LAM_DIR)

    from engines.defaults import default_config_parser, default_setup
    from engines.infer import INFER

    json_path = "/tmp/lam_pipeline_output.json"
    cfg = default_config_parser("configs/lam_audio2exp_config_streaming.py", {
        "audio_input": audio_path,
        "save_json_path": json_path,
        "save_path": "/tmp/lam_pipeline_exp",
    })
    cfg = default_setup(cfg)
    os.makedirs(cfg.save_path, exist_ok=True)

    infer = INFER.build(dict(type=cfg.infer.type, cfg=cfg))
    infer.infer()
    os.chdir(orig_cwd)

    with open(json_path) as f:
        data = json.load(f)

    names = data["names"]
    frames = data["frames"]
    print(f"  {len(frames)} expression frames @ 30fps ({len(frames)/30:.1f}s)")

    # Scale and convert
    scale_map = {
        "jawOpen": 5.0, "mouthLowerDownLeft": 2.5, "mouthLowerDownRight": 2.5,
        "mouthPucker": 3.0, "mouthFunnel": 3.0, "mouthSmileLeft": 2.0,
        "mouthSmileRight": 2.0, "mouthPressLeft": 2.0, "mouthPressRight": 2.0,
        "mouthUpperUpLeft": 2.0, "mouthUpperUpRight": 2.0, "mouthStretchLeft": 2.0,
        "mouthStretchRight": 2.0, "mouthFrownLeft": 2.0, "mouthFrownRight": 2.0,
        "eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0,
    }

    arkit_dicts = []
    for fi, frame in enumerate(frames):
        weights = frame["weights"]
        d = {}
        for i in range(len(names)):
            scale = scale_map.get(names[i], 2.0)
            d[names[i]] = min(weights[i] * scale, 1.0)
        # Synthetic head motion
        jaw_val = d.get("jawOpen", 0)
        d["headBoneX"] = 0.0
        d["headBoneY"] = np.sin(fi * 0.03) * 0.05 + jaw_val * 0.1
        d["headBoneZ"] = np.sin(fi * 0.02) * 0.03
        arkit_dicts.append(d)

    # Free LAM from GPU
    del infer
    import gc; gc.collect()
    torch.cuda.empty_cache()

    return arkit_dicts


# ─── Step 3: ARKit → THA4 Convert ────────────────────────────────────────────

def convert_arkit_to_tha4(arkit_frames):
    """Convert ARKit 52 blendshapes to THA4 45 parameters using built-in converter."""
    print(f"[3/4] ARKit 52 → THA4 45 conversion...")

    from tha4.mocap.ifacialmocap_pose_converter_25 import IFacialMocapPoseConverter25
    converter = IFacialMocapPoseConverter25()

    tha4_params = []
    for arkit_dict in arkit_frames:
        pose = converter.convert(arkit_dict)
        tha4_params.append(pose)

    # Smooth head pose
    params_array = np.array(tha4_params)
    for dim in [39, 40, 41, 42, 43]:
        alpha = 0.7
        for i in range(1, len(params_array)):
            params_array[i, dim] = alpha * params_array[i, dim] + (1 - alpha) * params_array[i-1, dim]

    print(f"  {len(tha4_params)} frames converted")
    return [params_array[i] for i in range(len(params_array))]


# ─── Step 4: THA4 Render ─────────────────────────────────────────────────────

def render_tha4(tha4_params_list, character_path, output_path, fps=30, teacher=False):
    """Render animation frames using THA4."""
    print(f"[4/4] THA4 Rendering ({len(tha4_params_list)} frames)...")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from PIL import Image as PILImage
    import cv2, imageio, subprocess

    char_dir = os.path.dirname(character_path)
    char_yaml = os.path.join(char_dir, "character_model.yaml")

    if os.path.exists(char_yaml) and not teacher:
        from tha4.charmodel.character_model import CharacterModel
        cm = CharacterModel.load(char_yaml)
        poser = cm.get_poser(device)
        char_image = cm.get_character_image(device)
        print(f"  Distilled model loaded")
    else:
        from tha4.poser.modes.mode_07 import create_poser
        poser = create_poser(device, default_output_index=5, skip_eyebrow=True)
        char_pil = PILImage.open(character_path).convert('RGBA')
        if char_pil.size != (512, 512):
            char_pil = char_pil.resize((512, 512), PILImage.BICUBIC)
        char_np = np.array(char_pil).astype(np.float32) / 255.0
        char_image = torch.from_numpy(char_np).permute(2, 0, 1).to(device)
        print(f"  Teacher model loaded")

    frames = []
    t0 = time.time()

    with torch.no_grad():
        for i, params in enumerate(tha4_params_list):
            pose_tensor = torch.tensor(params, device=device, dtype=torch.float32)
            output = poser.pose(char_image, pose_tensor, output_index=0)

            frame_rgba = output.squeeze(0).permute(1, 2, 0).detach().cpu().numpy()
            frame_rgba = np.clip(frame_rgba * 255, 0, 255).astype(np.uint8)
            alpha = frame_rgba[:, :, 3:4] / 255.0
            rgb = frame_rgba[:, :, :3]
            bg = np.ones_like(rgb) * 255
            frame_rgb = (rgb * alpha + bg * (1 - alpha)).astype(np.uint8)

            hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 0.85
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            frame_rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
            frames.append(frame_rgb)

    elapsed = time.time() - t0
    print(f"  Rendered in {elapsed:.1f}s ({len(frames)/elapsed:.1f} fps)")

    # Save with audio
    temp_video = output_path.replace(".mp4", "_nosound.mp4")
    with imageio.get_writer(temp_video, fps=fps) as writer:
        for frame in frames:
            writer.append_data(frame)

    # Mux audio (use the generated TTS audio)
    audio_path = output_path.replace(".mp4", "_audio.wav")
    if os.path.exists(audio_path):
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_video, "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-shortest", output_path
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(temp_video)
    else:
        os.rename(temp_video, output_path)

    return output_path


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="JPTAKU Full Pipeline: Text → TTS → Expression → Animation")
    parser.add_argument("--text", required=True, help="Japanese text to speak")
    parser.add_argument("--character", required=True, help="Character image (.png) or dir with character_model.yaml")
    parser.add_argument("--ref_audio", default=None, help="Reference voice audio for CosyVoice3 (optional)")
    parser.add_argument("--ref_text", default=None, help="Reference voice transcript (optional)")
    parser.add_argument("--output", default="outputs/full_pipeline.mp4", help="Output video path")
    parser.add_argument("--fps", type=int, default=30, help="Output FPS")
    parser.add_argument("--teacher", action="store_true", help="Force THA4 teacher model")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) or ".", exist_ok=True)

    # Use Japanese-Eroge-Voice-V2 dataset reference voice by default
    if args.ref_audio is None:
        ref_dir = os.path.join(PROJECT_ROOT, "assets", "reference_voice")
        args.ref_audio = os.path.join(ref_dir, "ref_00.wav")
        with open(os.path.join(ref_dir, "ref_00.txt")) as f:
            args.ref_text = f.read().strip()
        print(f"[INFO] Reference voice: Japanese-Eroge-Voice-V2")
        print(f"  Audio: {args.ref_audio}")
        print(f"  Text: {args.ref_text}")

    t_start = time.time()

    # Step 1: TTS
    tts_wav = args.output.replace(".mp4", "_audio.wav")
    run_cosyvoice_tts(args.text, args.ref_audio, args.ref_text, tts_wav)

    # Step 2: Audio → ARKit expressions
    arkit_frames = run_lam_inference(os.path.abspath(tts_wav))

    # Step 3: ARKit → THA4
    tha4_params = convert_arkit_to_tha4(arkit_frames)

    # Step 4: Render
    render_tha4(tha4_params, args.character, args.output, fps=args.fps, teacher=args.teacher)

    total = time.time() - t_start
    print(f"\n{'='*60}")
    print(f"  FULL PIPELINE DONE!")
    print(f"  Input: \"{args.text}\"")
    print(f"  Output: {args.output}")
    print(f"  Total time: {total:.1f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
