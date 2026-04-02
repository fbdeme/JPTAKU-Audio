"""
JPTAKU Chat Server — Full pipeline on single port:
  Text → GPT-4o-mini → CosyVoice3 TTS → A2F-3D BlendShapes → WebSocket stream

HTTP + WebSocket both on same port (8080).

Usage:
  uv run python chat_server.py --port 8080
"""

import argparse
import asyncio
import json
import os
import sys
import tempfile
import time
import wave
from pathlib import Path

import aiohttp.web
import pykakasi
import websockets
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

# ── CosyVoice3 Setup ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
COSYVOICE_DIR = PROJECT_ROOT / "CosyVoice"
MATCHA_DIR = COSYVOICE_DIR / "third_party" / "Matcha-TTS"
sys.path.insert(0, str(COSYVOICE_DIR))
sys.path.insert(0, str(MATCHA_DIR))

MODEL_DIR = str(PROJECT_ROOT / "pretrained_models" / "Fun-CosyVoice3-0.5B")
REF_AUDIO = str(PROJECT_ROOT / "assets" / "reference_voice" / "ref_00.wav")

kks = pykakasi.kakasi()
cosyvoice_model = None


def to_katakana(text: str) -> str:
    result = kks.convert(text)
    return "".join([item["kana"] for item in result])


def get_cosyvoice_model():
    global cosyvoice_model
    if cosyvoice_model is None:
        from cosyvoice.cli.cosyvoice import CosyVoice3
        print(f"[CosyVoice3] Loading model from {MODEL_DIR}...")
        cosyvoice_model = CosyVoice3(MODEL_DIR)
        print("[CosyVoice3] Model loaded!")
    return cosyvoice_model

SYSTEM_PROMPT = """あなたは「凛（りん）」という名前の日本語チューターです。
性格: 落ち着いた優しいお姉さんタイプ。丁寧だけど親しみやすい。
役割: ユーザーの日本語学習を手助けする。質問に日本語で答え、必要に応じて説明を加える。
話し方: 敬語とタメ語を混ぜた柔らかい話し方。短めの文で答える（1-3文程度）。
重要: 回答は必ず日本語のみで。長すぎないこと（50文字以内推奨）。"""

A2F_HOST = "localhost:52000"

ANIME_RELEVANT = {
    "JawOpen", "MouthFunnel", "MouthPucker", "MouthSmileLeft", "MouthSmileRight",
    "MouthFrownLeft", "MouthFrownRight", "EyeBlinkLeft", "EyeBlinkRight",
    "EyeWideLeft", "EyeWideRight", "BrowInnerUp", "BrowDownLeft", "BrowDownRight",
    "BrowOuterUpLeft", "BrowOuterUpRight", "CheekPuff",
}

openai_client = OpenAI()
chat_history = []
ws_clients: set = set()


def call_llm(user_text: str) -> str:
    chat_history.append({"role": "user", "content": user_text})
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": SYSTEM_PROMPT}] + chat_history[-10:],
        max_tokens=100,
        temperature=0.7,
    )
    reply = response.choices[0].message.content.strip()
    chat_history.append({"role": "assistant", "content": reply})
    return reply


def call_tts(text: str, output_path: str) -> str:
    import soundfile as sf

    model = get_cosyvoice_model()
    text_kata = to_katakana(text)

    output_list = list(model.inference_zero_shot(
        tts_text=text_kata + "<|endofprompt|>",
        prompt_text=to_katakana("こんにちは、今日はどうでしたか？") + "<|endofprompt|>",
        prompt_wav=REF_AUDIO,
        stream=False,
    ))

    if not output_list:
        raise RuntimeError("CosyVoice3 TTS output is empty")

    audio_tensor = output_list[0]["tts_speech"]
    # audio_tensor shape: (1, samples) → (samples,) numpy
    sf.write(output_path, audio_tensor.squeeze(0).cpu().numpy(), model.sample_rate)
    return output_path


async def call_a2f(wav_path: str) -> list[dict]:
    import grpc
    from nvidia_audio2face_3d.audio2face_pb2_grpc import A2FControllerServiceStub
    from nvidia_audio2face_3d import messages_pb2 as msg
    from nvidia_ace.audio_pb2 import AudioHeader

    with wave.open(wav_path, "rb") as wf:
        sr, ch, sw = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
        audio_bytes = wf.readframes(wf.getnframes())

    channel = grpc.aio.insecure_channel(A2F_HOST)
    stub = A2FControllerServiceStub(channel)
    stream = stub.ProcessAudioStream()

    await stream.write(msg.AudioWithEmotionStream(
        audio_stream_header=msg.AudioWithEmotionStreamHeader(
            audio_header=AudioHeader(
                samples_per_second=sr, bits_per_sample=sw * 8,
                channel_count=ch, audio_format=AudioHeader.AUDIO_FORMAT_PCM,
            ),
            emotion_post_processing_params=msg.EmotionPostProcessingParameters(
                emotion_contrast=1.0, live_blend_coef=0.7,
                enable_preferred_emotion=False, max_emotions=5,
            ),
            blendshape_params=msg.BlendShapeParameters(),
        )
    ))

    chunk_size = sr * sw * ch
    for offset in range(0, len(audio_bytes), chunk_size):
        await stream.write(msg.AudioWithEmotionStream(
            audio_with_emotion=msg.AudioWithEmotion(
                audio_buffer=audio_bytes[offset:offset + chunk_size])
        ))

    await stream.write(msg.AudioWithEmotionStream(
        end_of_audio=msg.AudioWithEmotionStream.EndOfAudio()))
    await stream.done_writing()

    bs_names, frames = [], []
    while True:
        resp = await stream.read()
        if resp == grpc.aio.EOF:
            break
        if resp.HasField("animation_data_stream_header"):
            bs_names = list(resp.animation_data_stream_header.skel_animation_header.blend_shapes)
        elif resp.HasField("animation_data"):
            for bs in resp.animation_data.skel_animation.blend_shape_weights:
                frame = {"time": bs.time_code, "blendshapes": {}}
                for name, w in zip(bs_names, bs.values):
                    if name in ANIME_RELEVANT:
                        frame["blendshapes"][name] = round(w, 4)
                frames.append(frame)
    await channel.close()
    return frames


async def broadcast(data: dict):
    global ws_clients
    if not ws_clients:
        return
    msg = json.dumps(data)
    dead = set()
    for client in ws_clients:
        try:
            await client.send(msg)
        except Exception:
            dead.add(client)
    ws_clients -= dead


async def stream_animation(frames: list[dict], audio_url: str, reply_text: str):
    print(f"[WS] Broadcasting {len(frames)} frames to {len(ws_clients)} clients")
    await broadcast({
        "type": "chat_response", "text": reply_text,
        "audio_url": audio_url, "n_frames": len(frames), "fps": 30,
    })
    await asyncio.sleep(0.05)
    for i, frame in enumerate(frames):
        t0 = asyncio.get_event_loop().time()
        await broadcast({
            "type": "frame", "index": i,
            "time": frame["time"], "blendshapes": frame["blendshapes"],
        })
        sleep = (1.0 / 30) - (asyncio.get_event_loop().time() - t0)
        if sleep > 0:
            await asyncio.sleep(sleep)
    await broadcast({"type": "end"})
    print("[WS] Broadcast complete")


# ── Handlers ────────────────────────────────────────────────────────────────

async def handle_chat(request):
    body = await request.json()
    user_text = body.get("text", "")
    if not user_text:
        return aiohttp.web.json_response({"error": "empty text"}, status=400)

    print(f"\n[Chat] User: {user_text}")
    loop = asyncio.get_event_loop()

    reply = await loop.run_in_executor(None, call_llm, user_text)
    print(f"[Chat] Rin: {reply}")

    wav_path = os.path.join(tempfile.gettempdir(), f"tts_{int(time.time()*1000)}.wav")
    await loop.run_in_executor(None, call_tts, reply, wav_path)
    print(f"[Chat] TTS: {wav_path}")

    frames = await call_a2f(wav_path)
    print(f"[Chat] A2F: {len(frames)} frames")

    audio_url = f"/audio/{os.path.basename(wav_path)}"
    asyncio.create_task(stream_animation(frames, audio_url, reply))

    return aiohttp.web.json_response({
        "text": reply, "audio_url": audio_url, "n_frames": len(frames),
    })


async def handle_audio(request):
    filename = request.match_info["filename"]
    filepath = os.path.join(tempfile.gettempdir(), filename)
    if not os.path.exists(filepath):
        return aiohttp.web.Response(status=404)
    return aiohttp.web.FileResponse(filepath, headers={
        "Content-Type": "audio/wav",
        "Access-Control-Allow-Origin": "*",
    })


async def ws_handler(websocket):
    """Handle WebSocket client (websockets library)."""
    ws_clients.add(websocket)
    print(f"[WS] Client connected ({len(ws_clients)} total)")
    try:
        await websocket.wait_closed()
    finally:
        ws_clients.discard(websocket)
        print(f"[WS] Client disconnected ({len(ws_clients)} total)")


async def handle_health(request):
    return aiohttp.web.json_response({"status": "ok"})


@aiohttp.web.middleware
async def cors_middleware(request, handler):
    if request.method == "OPTIONS":
        return aiohttp.web.Response(headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
        })
    response = await handler(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response


async def start_servers(http_port: int, ws_port: int):
    # HTTP server
    app = aiohttp.web.Application(middlewares=[cors_middleware])
    app.router.add_post("/chat", handle_chat)
    app.router.add_get("/audio/{filename}", handle_audio)
    app.router.add_get("/health", handle_health)

    runner = aiohttp.web.AppRunner(app)
    await runner.setup()
    await aiohttp.web.TCPSite(runner, "0.0.0.0", http_port).start()
    print(f"HTTP on http://0.0.0.0:{http_port}")

    # WebSocket server (websockets library — proven to work)
    print(f"WS on ws://0.0.0.0:{ws_port}")
    async with websockets.serve(ws_handler, "0.0.0.0", ws_port):
        await asyncio.Future()


def main():
    parser = argparse.ArgumentParser(description="JPTAKU Chat Server")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--ws-port", type=int, default=8765)
    args = parser.parse_args()

    asyncio.run(start_servers(args.port, args.ws_port))


if __name__ == "__main__":
    main()
