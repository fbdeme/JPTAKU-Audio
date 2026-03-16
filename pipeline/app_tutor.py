#!/usr/bin/env python3
"""
JPTAKU Interactive Japanese Tutor
Chat → LLM → TTS → Expression → Animation
"""
import os, sys, time, json, tempfile, gc
import numpy as np
import torch

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
LAM_DIR = os.path.join(PROJECT_ROOT, "LAM_Audio2Expression")
sys.path.insert(0, LAM_DIR)
# GPT-SoVITS runs as separate API server on port 9880

# wx stub + matplotlib fix
import types
_wx = types.ModuleType('wx')
for _a in ['Panel','BoxSizer','StaticText','VERTICAL','HORIZONTAL','ALL','EXPAND',
           'Slider','SL_HORIZONTAL','EVT_SLIDER','CheckBox','EVT_CHECKBOX',
           'Choice','EVT_CHOICE','Event','CommandEvent','ID_ANY','Button','EVT_BUTTON']:
    setattr(_wx, _a, type(_a, (), {'__init__': lambda s, *a, **k: None}))
_wx.VERTICAL=0;_wx.HORIZONTAL=1;_wx.ALL=0;_wx.EXPAND=0;_wx.SL_HORIZONTAL=0
_wx.EVT_SLIDER=None;_wx.EVT_CHECKBOX=None;_wx.EVT_CHOICE=None;_wx.EVT_BUTTON=None;_wx.ID_ANY=-1
_wx.GetApp = lambda: None
sys.modules['wx'] = _wx
import matplotlib; matplotlib.use('Agg')

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ─── Persona ─────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """あなたは「凛（りん）」という名前の日本語チューターです。
性格: 落ち着いた優しいお姉さんタイプ。丁寧だけど親しみやすい。
役割: ユーザーの日本語学習を手助けする。質問に日本語で答え、必要に応じて説明を加える。
話し方: 敬語とタメ語を混ぜた柔らかい話し方。短めの文で答える（1-3文程度）。
重要: 回答は必ず日本語のみで。長すぎないこと（50文字以内推奨）。"""

REF_AUDIO = os.path.join(PROJECT_ROOT, "assets/reference_voice/tsumugi/tsumugi_04.wav")
REF_PROMPT_TEXT = "えへへ、日本語って楽しいでしょ？もっと色んな言葉を覚えようね。"

# ─── Model Loading (all at startup) ─────────────────────────────────────────

def load_all_models():
    """Load all models once at startup."""
    global cosyvoice_model, lam_infer_engine, lam_cfg, tha4_poser, tha4_char_image, tha4_converter, openai_client

    print("[1/4] Loading OpenAI client...")
    from openai import OpenAI
    openai_client = OpenAI()

    print("[2/4] Checking GPT-SoVITS API...")
    import requests
    try:
        requests.get("http://127.0.0.1:9880/control", timeout=3)
        print("  GPT-SoVITS API: OK")
    except:
        print("  WARNING: GPT-SoVITS not running! Start it:")
        print("  cd /root/JPTAKU-Audio/GPT-SoVITS && python api_v2.py -a 127.0.0.1 -p 9880 -c /tmp/tts_v2proplus.yaml")

    print("[3/4] Loading LAM-Audio2Expression...")
    orig_cwd = os.getcwd()
    os.chdir(LAM_DIR)
    from engines.defaults import default_config_parser, default_setup
    from engines.infer import INFER
    lam_cfg = default_config_parser("configs/lam_audio2exp_config_streaming.py", {})
    lam_cfg = default_setup(lam_cfg)
    lam_infer_engine = INFER.build(dict(type=lam_cfg.infer.type, cfg=lam_cfg))
    os.chdir(orig_cwd)

    print("[4/4] Loading THA4...")
    from tha4.charmodel.character_model import CharacterModel
    cm = CharacterModel.load("data/character_models/lambda_00/character_model.yaml")
    tha4_poser = cm.get_poser(DEVICE)
    tha4_char_image = cm.get_character_image(DEVICE)
    from tha4.mocap.ifacialmocap_pose_converter_25 import IFacialMocapPoseConverter25
    tha4_converter = IFacialMocapPoseConverter25()

    print("All models loaded!")


# ─── Pipeline Functions ──────────────────────────────────────────────────────

def llm_respond(user_message, history):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_msg, bot_msg in history:
        messages.append({"role": "user", "content": user_msg})
        if bot_msg:
            messages.append({"role": "assistant", "content": bot_msg})
    messages.append({"role": "user", "content": user_message})
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini", messages=messages, max_tokens=100, temperature=0.7)
    return resp.choices[0].message.content


def tts_speak(text):
    """Generate speech via GPT-SoVITS with SBV2-clean reference."""
    import requests, soundfile as sf
    path = tempfile.mktemp(suffix=".wav")
    resp = requests.post("http://127.0.0.1:9880/tts", json={
        "text": text,
        "text_lang": "ja",
        "ref_audio_path": REF_AUDIO,
        "prompt_text": REF_PROMPT_TEXT,
        "prompt_lang": "ja",
        "text_split_method": "cut5",
        "speed_factor": 1.0,
        "streaming_mode": False,
    })
    if resp.status_code != 200:
        print(f"TTS Error: {resp.text}")
        return None, 0
    with open(path, "wb") as f:
        f.write(resp.content)
    data, sr = sf.read(path)
    return path, len(data) / sr


def audio_to_arkit(wav_path):
    """Run LAM inference using pre-loaded engine."""
    orig_cwd = os.getcwd()
    os.chdir(LAM_DIR)

    # Update config for this audio
    lam_cfg.audio_input = wav_path
    json_path = tempfile.mktemp(suffix=".json")
    lam_cfg.save_json_path = json_path
    lam_cfg.save_path = tempfile.mkdtemp()

    lam_infer_engine.infer()
    os.chdir(orig_cwd)

    with open(json_path) as f:
        data = json.load(f)

    names = data["names"]
    scale_map = {"jawOpen": 5.0, "mouthLowerDownLeft": 2.5, "mouthLowerDownRight": 2.5,
                 "mouthPucker": 3.0, "mouthFunnel": 3.0, "mouthSmileLeft": 2.0,
                 "mouthSmileRight": 2.0, "eyeBlinkLeft": 1.0, "eyeBlinkRight": 1.0}

    arkit_dicts = []
    for fi, frame in enumerate(data["frames"]):
        w = frame["weights"]
        d = {names[i]: min(w[i] * scale_map.get(names[i], 2.0), 1.0) for i in range(len(names))}
        jaw = d.get("jawOpen", 0)
        d["headBoneX"] = 0.0
        d["headBoneY"] = np.sin(fi * 0.03) * 0.05 + jaw * 0.1
        d["headBoneZ"] = np.sin(fi * 0.02) * 0.03
        arkit_dicts.append(d)
    return arkit_dicts


def render_video(arkit_frames, wav_path):
    import cv2, imageio, subprocess

    params_list = [tha4_converter.convert(d) for d in arkit_frames]
    arr = np.array(params_list)
    for dim in [39, 40, 41, 42, 43]:
        for i in range(1, len(arr)):
            arr[i, dim] = 0.7 * arr[i, dim] + 0.3 * arr[i-1, dim]

    frames = []
    with torch.no_grad():
        for p in arr:
            pose = torch.tensor(p, device=DEVICE, dtype=torch.float32)
            out = tha4_poser.pose(tha4_char_image, pose, output_index=0)
            rgba = out.squeeze(0).permute(1, 2, 0).detach().cpu().numpy()
            rgba = np.clip(rgba * 255, 0, 255).astype(np.uint8)
            a = rgba[:, :, 3:4] / 255.0
            rgb = (rgba[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
            hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV).astype(np.float32)
            hsv[:, :, 1] *= 0.85; hsv[:, :, 1] = np.clip(hsv[:, :, 1], 0, 255)
            frames.append(cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB))

    video_path = tempfile.mktemp(suffix=".mp4")
    silent = video_path.replace(".mp4", "_s.mp4")
    with imageio.get_writer(silent, fps=30) as w:
        for f in frames: w.append_data(f)
    subprocess.run(["ffmpeg", "-y", "-i", silent, "-i", wav_path,
                    "-c:v", "copy", "-c:a", "aac", "-shortest", video_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if os.path.exists(silent): os.remove(silent)
    return video_path


# ─── Chat Handler ────────────────────────────────────────────────────────────

def chat_and_animate(user_message, history):
    if not user_message.strip():
        return history, None, None, ""

    t0 = time.time()

    # LLM
    reply = llm_respond(user_message, history)
    history.append((user_message, reply))
    yield history, None, None, f"Generating voice..."

    # TTS
    wav, dur = tts_speak(reply)
    if not wav:
        yield history, None, None, "TTS failed"
        return
    yield history, None, wav, f"Voice: {dur:.1f}s. Generating expressions..."

    # Expression
    arkit = audio_to_arkit(os.path.abspath(wav))
    yield history, None, wav, f"{len(arkit)} frames. Rendering..."

    # Render
    video = render_video(arkit, wav)
    yield history, video, wav, f"Done in {time.time()-t0:.1f}s ({len(arkit)} frames)"


# ─── UI ──────────────────────────────────────────────────────────────────────

def build_ui():
    import gradio as gr

    with gr.Blocks(title="JPTAKU Japanese Tutor") as demo:
        gr.Markdown("# JPTAKU - Japanese Tutor \"Rin\"")
        gr.Markdown("Ask anything in any language. Rin will respond in Japanese with voice and animation.")

        with gr.Row():
            with gr.Column(scale=1):
                chatbot = gr.Chatbot(label="Chat", height=400)
                with gr.Row():
                    msg = gr.Textbox(placeholder="Type your message...", scale=4, show_label=False)
                    btn = gr.Button("Send", variant="primary", scale=1)
                status = gr.Textbox(label="Status", interactive=False, lines=2)

            with gr.Column(scale=1):
                video = gr.Video(label="Rin's Response", height=400, autoplay=True)
                audio = gr.Audio(label="Voice", visible=False)

        btn.click(chat_and_animate, [msg, chatbot], [chatbot, video, audio, status]).then(lambda: "", outputs=msg)
        msg.submit(chat_and_animate, [msg, chatbot], [chatbot, video, audio, status]).then(lambda: "", outputs=msg)

    return demo


if __name__ == "__main__":
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    print("=" * 50)
    print("  JPTAKU Japanese Tutor - Loading models...")
    print("=" * 50)
    load_all_models()
    print("Starting web server on http://0.0.0.0:7860")
    demo = build_ui()
    demo.queue()
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, show_error=True)
