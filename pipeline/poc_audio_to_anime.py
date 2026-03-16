#!/usr/bin/env python3
"""
Audio → DiffPoseTalk → FLAME → THA4 Bridge → Anime Animation
Rule-based FLAME-to-THA4 mapping (Method A).
"""
import os
import sys
import time
import argparse
import numpy as np
import torch
from PIL import Image

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "SkyReels-A1"))

from tha4.charmodel.character_model import CharacterModel

# ─── FLAME → THA4 Bridge (Method A: Rule-based) ─────────────────────────────

class FLAMEToTHA4Bridge:
    """
    Maps DiffPoseTalk FLAME coefficients to THA4's 45 pose parameters.

    THA4 parameter layout (45 params, 30 groups with arity):
      0-11: eyebrow (6 groups × arity 2) = [troubled_L, troubled_R, angry_L, angry_R, ...]
     12-23: eye (6 groups × arity 2)
     24-25: iris_small (arity 2)
        26: mouth_aaa
        27: mouth_iii
        28: mouth_uuu
        29: mouth_eee
        30: mouth_ooo
        31: mouth_delta
     32-33: mouth_lowered_corner (arity 2)
     34-35: mouth_raised_corner (arity 2)
        36: mouth_smirk
        37: iris_rotation_x (-1~1)
        38: iris_rotation_y (-1~1)
        39: head_x (-1~1, yaw)
        40: head_y (-1~1, pitch)
        41: neck_z (-1~1, roll)
        42: body_y (-1~1)
        43: body_z (-1~1)
        44: breathing (0~1)
    """

    def __init__(self):
        self.frame_count = 0

    def convert(self, exp, jaw, pose, eyelid=None):
        """
        Conservative rule-based mapping.
        Only maps what we can reliably derive from FLAME outputs:
          - jaw_open → mouth_aaa (primary lip sync)
          - pose → head rotation
          - periodic blink / breathing for liveliness
        Does NOT map FLAME PCA expression dims to eyes/eyebrows
        (those are learned components with no guaranteed semantic meaning).
        """
        params = np.zeros(45, dtype=np.float32)

        # ── Head Pose ──
        # FLAME pose range: pitch[-0.05,0.17], yaw[-0.16,0.07], roll[-0.09,-0.01]
        params[39] = np.clip(pose[1] / 0.15, -0.5, 0.5)    # head_x (yaw)
        params[40] = np.clip(-pose[0] / 0.15, -0.4, 0.4)   # head_y (pitch)
        params[41] = np.clip(pose[2] / 0.10, -0.3, 0.3)    # neck_z (roll)

        # Body follow
        params[42] = params[39] * 0.3   # body_y
        params[43] = params[41] * 0.2   # body_z

        # ── Mouth ──
        # jaw[0] observed range: [0.01, 0.20]
        jaw_open = np.clip((jaw[0] - 0.01) / 0.12, 0, 1)

        # Primary: mouth_aaa scales with jaw
        params[26] = np.clip(jaw_open * 1.0, 0, 0.8)    # mouth_aaa (あ)

        # Secondary vowels based on jaw opening level
        params[27] = np.clip((0.5 - jaw_open) * 1.5, 0, 0.4) * jaw_open * 2.5  # mouth_iii (small open)
        params[28] = np.clip((0.4 - jaw_open) * 2.0, 0, 0.3) * jaw_open * 2.5  # mouth_uuu (small open)
        params[30] = np.clip(jaw_open * 0.5, 0, 0.4)    # mouth_ooo

        # ── Eyes (blink works with skip_eyebrow!) ──
        blink = 0.0
        blink_period = 90 + (self.frame_count // 90) % 50
        blink_phase = self.frame_count % blink_period
        if blink_phase < 3:
            blink = [0.0, 0.85, 0.0][blink_phase]
        params[12] = blink  # eye_wink_L
        params[13] = blink  # eye_wink_R

        # ── Breathing ──
        params[44] = (np.sin(self.frame_count * 0.05) + 1) * 0.3

        self.frame_count += 1
        return params


# ─── Main Pipeline ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Audio → FLAME → THA4 Anime Pipeline")
    parser.add_argument("--audio", required=True, help="Input audio file (.wav)")
    parser.add_argument("--character", default="data/character_models/lambda_00/character_model.yaml",
                        help="THA4 character model YAML")
    parser.add_argument("--output", default="output_tha4.mp4", help="Output video path")
    parser.add_argument("--fps", type=int, default=25, help="Output FPS")
    parser.add_argument("--teacher", action="store_true", help="Force teacher model (skip_eyebrow)")
    args = parser.parse_args()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # ── Step 1: Load THA4 Character ──
    print("[1/4] Loading THA4 model...")

    # Load character image
    from PIL import Image as PILImage
    char_pil = PILImage.open(args.character).convert('RGBA')
    if char_pil.size != (512, 512):
        char_pil = char_pil.resize((512, 512), PILImage.BICUBIC)
    char_np = np.array(char_pil).astype(np.float32) / 255.0
    char_image = torch.from_numpy(char_np).permute(2, 0, 1).to(device)

    # Check if a distilled character model exists (YAML alongside image)
    char_dir = os.path.dirname(args.character)
    char_yaml = os.path.join(char_dir, "character_model.yaml")
    if os.path.exists(char_yaml) and not args.teacher:
        from tha4.charmodel.character_model import CharacterModel as CM
        cm = CM.load(char_yaml)
        poser = cm.get_poser(device)
        char_image = cm.get_character_image(device)
        print(f"  Distilled model loaded from {char_yaml}")
    else:
        from tha4.poser.modes.mode_07 import create_poser as create_teacher_poser
        poser = create_teacher_poser(device, default_output_index=5, skip_eyebrow=True)
        print(f"  Teacher model loaded (skip_eyebrow=True, output_index=5)")

    num_params = poser.get_num_parameters()
    print(f"  {num_params} params, image: {char_image.shape}")

    # ── Step 2: Run DiffPoseTalk ──
    print("[2/4] Running DiffPoseTalk (audio → FLAME)...")
    from diffposetalk.diffposetalk import DiffPoseTalk, DiffPoseTalkConfig
    skyreels_dir = os.path.join(os.path.dirname(__file__), "..", "SkyReels-A1")
    dpt_config = DiffPoseTalkConfig(
        model_path=os.path.join(skyreels_dir, "pretrained_models/diffposetalk/iter_0110000.pt"),
        coef_stats=os.path.join(skyreels_dir, "pretrained_models/diffposetalk/stats_train.npz"),
        style_path=os.path.join(skyreels_dir, "pretrained_models/diffposetalk/style/L4H4-T0.1-BS32/iter_0034000/normal.npy"),
    )
    dpt = DiffPoseTalk(config=dpt_config)
    shape_params = np.zeros(100)  # neutral face shape
    flame_outputs = dpt.infer_from_file(args.audio, shape_params)
    num_frames = len(flame_outputs)
    print(f"  Generated {num_frames} FLAME motion frames @ 25fps ({num_frames/25:.1f}s)")

    # Free DiffPoseTalk from GPU
    del dpt
    import gc; gc.collect()
    torch.cuda.empty_cache()

    # ── Step 3: FLAME → THA4 Bridge ──
    print("[3/4] Converting FLAME → THA4 parameters...")
    bridge = FLAMEToTHA4Bridge()
    tha4_params_list = []

    for frame in flame_outputs:
        exp = frame['expression_params'].squeeze().cpu().numpy()
        jaw = frame['jaw_params'].squeeze().cpu().numpy()
        pose_val = frame['pose_params'].squeeze().cpu().numpy()
        tha4_params = bridge.convert(exp, jaw, pose_val)
        tha4_params_list.append(tha4_params)

    # Light smoothing: only on head pose to avoid jitter, keep mouth responsive
    tha4_params_array = np.array(tha4_params_list)
    head_dims = [39, 40, 41, 42, 43]  # head_x, head_y, neck_z, body_y, body_z
    for dim in head_dims:
        alpha = 0.7  # lighter smoothing
        for i in range(1, len(tha4_params_array)):
            tha4_params_array[i, dim] = alpha * tha4_params_array[i, dim] + (1 - alpha) * tha4_params_array[i-1, dim]
    tha4_params_list = [tha4_params_array[i] for i in range(len(tha4_params_array))]
    print(f"  Converted {len(tha4_params_list)} frames (head pose smoothed)")

    # ── Step 4: Render with THA4 ──
    print(f"[4/4] Rendering {num_frames} frames with THA4...")
    frames = []
    t0 = time.time()

    with torch.no_grad():
        for i, params in enumerate(tha4_params_list):
            pose_tensor = torch.tensor(params, device=device, dtype=torch.float32)
            output = poser.pose(char_image, pose_tensor, output_index=0)

            # Convert RGBA tensor to RGB numpy
            frame_rgba = output.squeeze(0).permute(1, 2, 0).detach().cpu().numpy()
            frame_rgba = np.clip(frame_rgba * 255, 0, 255).astype(np.uint8)

            # Alpha composite on white background
            alpha = frame_rgba[:, :, 3:4] / 255.0
            rgb = frame_rgba[:, :, :3]
            bg = np.ones_like(rgb) * 255
            frame_rgb = (rgb * alpha + bg * (1 - alpha)).astype(np.uint8)

            # Desaturate slightly to match original art style
            import cv2
            hsv = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 0.85  # reduce saturation by 15%
            hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            frame_rgb = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)
            frames.append(frame_rgb)

            if (i + 1) % 100 == 0 or i == 0:
                elapsed = time.time() - t0
                fps_actual = (i + 1) / elapsed
                print(f"  Frame {i+1}/{num_frames} ({fps_actual:.1f} fps)")

    elapsed = time.time() - t0
    print(f"  Rendered {num_frames} frames in {elapsed:.1f}s ({num_frames/elapsed:.1f} fps)")

    # ── Save video ──
    print("Saving video...")
    import imageio
    temp_video = args.output.replace(".mp4", "_nosound.mp4")
    with imageio.get_writer(temp_video, fps=args.fps) as writer:
        for frame in frames:
            writer.append_data(frame)

    # Mux audio
    import subprocess
    subprocess.run([
        "ffmpeg", "-y", "-i", temp_video, "-i", args.audio,
        "-c:v", "copy", "-c:a", "aac", "-shortest", args.output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(temp_video)

    print(f"\n{'='*60}")
    print(f"  DONE! {args.output}")
    print(f"  Duration: {num_frames/args.fps:.1f}s, FPS: {args.fps}, Render: {num_frames/elapsed:.1f} fps")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
