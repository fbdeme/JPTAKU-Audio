#!/usr/bin/env python3
"""
JPTAKU Full Pipeline PoC:
  Audio (WAV) → LAM-Audio2Expression (ARKit 52) → THA4 ifacialmocap converter → THA4 Render → Video

Uses THA4's built-in ifacialmocap_pose_converter_25 for ARKit→THA4 mapping.
"""
import os
import sys
import time
import json
import argparse
import numpy as np
import torch

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
LAM_DIR = os.path.join(os.path.dirname(__file__), "..", "LAM_Audio2Expression")
sys.path.insert(0, LAM_DIR)

# wx stub (THA4 converter imports wx for GUI but we only need the conversion logic)
import types
_wx = types.ModuleType('wx')
for _attr in ['Panel','BoxSizer','StaticText','VERTICAL','HORIZONTAL','ALL','EXPAND',
              'Slider','SL_HORIZONTAL','EVT_SLIDER','CheckBox','EVT_CHECKBOX',
              'Choice','EVT_CHOICE','Event','CommandEvent','ID_ANY','Button','EVT_BUTTON']:
    if not hasattr(_wx, _attr):
        setattr(_wx, _attr, type(_attr, (), {'__init__': lambda self, *a, **k: None}))
_wx.VERTICAL = 0; _wx.HORIZONTAL = 1; _wx.ALL = 0; _wx.EXPAND = 0
_wx.SL_HORIZONTAL = 0; _wx.EVT_SLIDER = None; _wx.EVT_CHECKBOX = None
_wx.EVT_CHOICE = None; _wx.EVT_BUTTON = None; _wx.ID_ANY = -1
sys.modules['wx'] = _wx


def run_lam_inference(audio_path, lam_dir):
    """Run LAM-Audio2Expression and return per-frame ARKit 52 blendshape dicts."""
    print("[1/3] Running LAM-Audio2Expression...")

    orig_cwd = os.getcwd()
    os.chdir(lam_dir)

    from engines.defaults import default_config_parser, default_setup
    from engines.infer import INFER

    cfg = default_config_parser("configs/lam_audio2exp_config_streaming.py", {
        "audio_input": audio_path,
        "save_json_path": "/tmp/lam_output.json",
        "save_path": "/tmp/lam_exp",
    })
    cfg = default_setup(cfg)
    os.makedirs(cfg.save_path, exist_ok=True)

    infer = INFER.build(dict(type=cfg.infer.type, cfg=cfg))
    infer.infer()

    os.chdir(orig_cwd)

    # Parse output
    with open(cfg.save_json_path) as f:
        data = json.load(f)

    names = data["names"]  # 52 ARKit BlendShape names
    frames = data["frames"]

    print(f"  {len(frames)} frames @ 30fps ({len(frames)/30:.1f}s)")
    print(f"  BlendShapes: {len(names)}")

    # Convert to list of dicts with value amplification
    # LAM outputs are much smaller than real iFacialMocap values, need scaling
    scale_map = {
        "jawOpen": 5.0,           # LAM max ~0.22, need 0.5+ for visible mouth
        "mouthLowerDownLeft": 2.5,
        "mouthLowerDownRight": 2.5,
        "mouthShrugUpper": 1.0,   # don't over-amplify (causes raised_corner)
        "mouthPucker": 3.0,
        "mouthFunnel": 3.0,
        "mouthPressLeft": 2.0,
        "mouthPressRight": 2.0,
        "mouthUpperUpLeft": 2.0,
        "mouthUpperUpRight": 2.0,
        "mouthSmileLeft": 2.0,
        "mouthSmileRight": 2.0,
        "mouthFrownLeft": 2.0,
        "mouthFrownRight": 2.0,
        "mouthStretchLeft": 2.0,
        "mouthStretchRight": 2.0,
        "eyeBlinkLeft": 1.0,     # already 0~0.9, good
        "eyeBlinkRight": 1.0,
        "cheekPuff": 1.0,
        "noseSneerLeft": 1.0,
        "noseSneerRight": 1.0,
    }
    default_scale = 2.0

    arkit_dicts = []
    for fi, frame in enumerate(frames):
        weights = frame["weights"]
        d = {}
        for i in range(len(names)):
            scale = scale_map.get(names[i], default_scale)
            d[names[i]] = min(weights[i] * scale, 1.0)

        # Head rotation: LAM doesn't output it, generate subtle motion from audio energy
        # Use jaw movement as proxy for head liveliness
        jaw_val = d.get("jawOpen", 0)
        d["headBoneX"] = 0.0
        d["headBoneY"] = np.sin(fi * 0.03) * 0.05 + jaw_val * 0.1   # subtle nod with speech
        d["headBoneZ"] = np.sin(fi * 0.02) * 0.03
        arkit_dicts.append(d)

    return arkit_dicts


def main():
    parser = argparse.ArgumentParser(description="LAM → THA4 Full Pipeline")
    parser.add_argument("--audio", required=True, help="Input audio (.wav)")
    parser.add_argument("--character", required=True, help="Character image (512x512 RGBA .png) or character_model.yaml")
    parser.add_argument("--output", default="output_pipeline.mp4", help="Output video")
    parser.add_argument("--fps", type=int, default=30, help="Output FPS (match LAM's 30fps)")
    parser.add_argument("--teacher", action="store_true", help="Force teacher model")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ── Load THA4 ──
    print("[0/3] Loading THA4...")
    from PIL import Image as PILImage

    char_dir = os.path.dirname(args.character)
    char_yaml = os.path.join(char_dir, "character_model.yaml")

    if os.path.exists(char_yaml) and not args.teacher:
        from tha4.charmodel.character_model import CharacterModel
        cm = CharacterModel.load(char_yaml)
        poser = cm.get_poser(device)
        char_image = cm.get_character_image(device)
        print(f"  Distilled model: {poser.get_num_parameters()} params")
    else:
        from tha4.poser.modes.mode_07 import create_poser
        poser = create_poser(device, default_output_index=5, skip_eyebrow=True)
        char_pil = PILImage.open(args.character).convert('RGBA')
        if char_pil.size != (512, 512):
            char_pil = char_pil.resize((512, 512), PILImage.BICUBIC)
        char_np = np.array(char_pil).astype(np.float32) / 255.0
        char_image = torch.from_numpy(char_np).permute(2, 0, 1).to(device)
        print(f"  Teacher model (skip_eyebrow): {poser.get_num_parameters()} params")

    # ── Load THA4 pose converter ──
    from tha4.mocap.ifacialmocap_pose_converter_25 import IFacialMocapPoseConverter25
    converter = IFacialMocapPoseConverter25()

    # ── Run LAM ──
    audio_abs = os.path.abspath(args.audio)
    arkit_frames = run_lam_inference(audio_abs, LAM_DIR)

    # ── Convert ARKit → THA4 ──
    print("[2/3] Converting ARKit 52 → THA4 45...")
    tha4_params_list = []
    for arkit_dict in arkit_frames:
        tha4_pose = converter.convert(arkit_dict)
        tha4_params_list.append(tha4_pose)

    # Light smoothing on head pose only
    params_array = np.array(tha4_params_list)
    head_dims = [39, 40, 41, 42, 43]
    for dim in head_dims:
        alpha = 0.7
        for i in range(1, len(params_array)):
            params_array[i, dim] = alpha * params_array[i, dim] + (1 - alpha) * params_array[i-1, dim]
    tha4_params_list = [params_array[i] for i in range(len(params_array))]
    print(f"  {len(tha4_params_list)} frames converted")

    # ── Render ──
    print(f"[3/3] Rendering {len(tha4_params_list)} frames...")
    import cv2
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

            # Slight desaturation
            hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 0.85
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            frame_rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

            frames.append(frame_rgb)

            if (i + 1) % 100 == 0:
                fps_actual = (i + 1) / (time.time() - t0)
                print(f"  Frame {i+1}/{len(tha4_params_list)} ({fps_actual:.1f} fps)")

    elapsed = time.time() - t0
    print(f"  Rendered in {elapsed:.1f}s ({len(frames)/elapsed:.1f} fps)")

    # ── Save video ──
    print("Saving video...")
    import imageio
    import subprocess

    os.makedirs(os.path.dirname(os.path.abspath(args.output)) if os.path.dirname(args.output) else ".", exist_ok=True)

    temp_video = args.output.replace(".mp4", "_nosound.mp4")
    with imageio.get_writer(temp_video, fps=args.fps) as writer:
        for frame in frames:
            writer.append_data(frame)

    subprocess.run([
        "ffmpeg", "-y", "-i", temp_video, "-i", args.audio,
        "-c:v", "copy", "-c:a", "aac", "-shortest", args.output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if os.path.exists(temp_video):
        os.remove(temp_video)

    print(f"\n{'='*60}")
    print(f"  DONE! {args.output}")
    print(f"  Duration: {len(frames)/args.fps:.1f}s @ {args.fps}fps")
    print(f"  Render speed: {len(frames)/elapsed:.1f} fps")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
