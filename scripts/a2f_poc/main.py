"""
A2F-3D PoC: Audio → ARKit 52 BlendShapes

Modes:
  --a2f   : Use local A2F-3D Docker service (gRPC on localhost:52000)
  --dummy : Generate synthetic blendshape data for testing

Usage:
  uv run python main.py --a2f ../../assets/reference_voice/tsumugi/tsumugi_04.wav -o blendshapes.json
  uv run python main.py --dummy ../../assets/reference_voice/tsumugi/tsumugi_04.wav -o blendshapes.json
"""

import argparse
import asyncio
import json
import math
import wave


# Subset relevant for 2D anime face (PascalCase as output by A2F)
ANIME_RELEVANT = {
    "JawOpen", "MouthFunnel", "MouthPucker", "MouthSmileLeft", "MouthSmileRight",
    "MouthFrownLeft", "MouthFrownRight", "EyeBlinkLeft", "EyeBlinkRight",
    "EyeWideLeft", "EyeWideRight", "BrowInnerUp", "BrowDownLeft", "BrowDownRight",
    "BrowOuterUpLeft", "BrowOuterUpRight", "CheekPuff",
}


def read_wav_info(path: str) -> dict:
    with wave.open(path, "rb") as wf:
        return {
            "sample_rate": wf.getframerate(),
            "channels": wf.getnchannels(),
            "sample_width": wf.getsampwidth(),
            "n_frames": wf.getnframes(),
            "duration": wf.getnframes() / wf.getframerate(),
        }


def generate_dummy_blendshapes(duration: float, fps: int = 30) -> list[dict]:
    n_frames = int(duration * fps)
    frames = []
    for i in range(n_frames):
        t = i / fps
        frame = {"time": round(t, 4), "blendshapes": {}}
        jaw = max(0, math.sin(t * 8) * 0.4 + math.sin(t * 13) * 0.2)
        frame["blendshapes"]["jawOpen"] = round(jaw, 4)
        funnel = max(0, math.sin(t * 5 + 1) * 0.3)
        frame["blendshapes"]["mouthFunnel"] = round(funnel, 4)
        smile = max(0, math.sin(t * 2) * 0.15 + 0.1)
        frame["blendshapes"]["mouthSmileLeft"] = round(smile, 4)
        frame["blendshapes"]["mouthSmileRight"] = round(smile, 4)
        blink_cycle = t % 4.0
        blink = max(0, 1.0 - abs(blink_cycle - 3.8) * 10) if blink_cycle > 3.6 else 0
        frame["blendshapes"]["eyeBlinkLeft"] = round(blink, 4)
        frame["blendshapes"]["eyeBlinkRight"] = round(blink, 4)
        brow = max(0, math.sin(t * 1.5) * 0.2)
        frame["blendshapes"]["browInnerUp"] = round(brow, 4)
        frames.append(frame)
    return frames


def run_dummy(audio_path: str, output_path: str, fps: int = 30):
    info = read_wav_info(audio_path)
    print(f"Audio: {info['duration']:.2f}s, {info['sample_rate']}Hz, {info['channels']}ch")
    frames = generate_dummy_blendshapes(info["duration"], fps)
    result = {
        "source": "dummy",
        "audio_file": audio_path,
        "fps": fps,
        "duration": info["duration"],
        "n_frames": len(frames),
        "blendshape_names": sorted(ANIME_RELEVANT),
        "frames": frames,
    }
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Generated {len(frames)} frames -> {output_path}")


async def run_a2f(audio_path: str, output_path: str, host: str = "localhost:52000"):
    """Call local A2F-3D Docker service via bidirectional gRPC stream."""
    import grpc
    from nvidia_audio2face_3d.audio2face_pb2_grpc import A2FControllerServiceStub
    from nvidia_audio2face_3d import messages_pb2 as msg
    from nvidia_ace.audio_pb2 import AudioHeader

    info = read_wav_info(audio_path)
    print(f"Audio: {info['duration']:.2f}s, {info['sample_rate']}Hz, {info['channels']}ch")

    with wave.open(audio_path, "rb") as wf:
        audio_bytes = wf.readframes(wf.getnframes())

    channel = grpc.aio.insecure_channel(host)
    stub = A2FControllerServiceStub(channel)

    # Open bidirectional stream
    stream = stub.ProcessAudioStream()

    # 1) Send header
    header = msg.AudioWithEmotionStream(
        audio_stream_header=msg.AudioWithEmotionStreamHeader(
            audio_header=AudioHeader(
                samples_per_second=info["sample_rate"],
                bits_per_sample=info["sample_width"] * 8,
                channel_count=info["channels"],
                audio_format=AudioHeader.AUDIO_FORMAT_PCM,
            ),
            emotion_post_processing_params=msg.EmotionPostProcessingParameters(
                emotion_contrast=1.0,
                live_blend_coef=0.7,
                enable_preferred_emotion=False,
                max_emotions=5,
            ),
            blendshape_params=msg.BlendShapeParameters(),
        )
    )
    await stream.write(header)
    print("Sent header")

    # 2) Send audio in 1-second chunks
    chunk_samples = info["sample_rate"]
    bytes_per_sample = info["sample_width"] * info["channels"]
    chunk_size = chunk_samples * bytes_per_sample

    chunk_count = 0
    for offset in range(0, len(audio_bytes), chunk_size):
        chunk = audio_bytes[offset:offset + chunk_size]
        await stream.write(
            msg.AudioWithEmotionStream(
                audio_with_emotion=msg.AudioWithEmotion(audio_buffer=chunk)
            )
        )
        chunk_count += 1

    print(f"Sent {chunk_count} audio chunks")

    # 3) Send end of audio
    await stream.write(
        msg.AudioWithEmotionStream(
            end_of_audio=msg.AudioWithEmotionStream.EndOfAudio()
        )
    )
    await stream.done_writing()
    print("Sent end-of-audio, reading responses...")

    # 4) Read responses
    bs_names = []
    frames = []

    while True:
        response = await stream.read()
        if response == grpc.aio.EOF:
            break

        if response.HasField("animation_data_stream_header"):
            hdr = response.animation_data_stream_header
            bs_names = list(hdr.skel_animation_header.blend_shapes)
            print(f"BlendShape names ({len(bs_names)}): {bs_names[:5]}...")

        elif response.HasField("animation_data"):
            for bs_data in response.animation_data.skel_animation.blend_shape_weights:
                frame = {"time": bs_data.time_code, "blendshapes": {}}
                for name, weight in zip(bs_names, bs_data.values):
                    frame["blendshapes"][name] = round(weight, 4)
                frames.append(frame)
            print(".", end="", flush=True)

        elif response.HasField("status"):
            status = response.status
            print(f"\nStatus: code={status.code}, message={status.message}")

    await channel.close()

    # Filter to anime-relevant blendshapes
    for frame in frames:
        frame["blendshapes"] = {
            k: v for k, v in frame["blendshapes"].items() if k in ANIME_RELEVANT
        }

    result = {
        "source": "nvidia_a2f_3d_local",
        "audio_file": audio_path,
        "fps": 30,
        "duration": info["duration"],
        "n_frames": len(frames),
        "blendshape_names": bs_names,
        "anime_relevant": sorted(ANIME_RELEVANT),
        "frames": frames,
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    print(f"\nReceived {len(frames)} frames -> {output_path}")


def main():
    parser = argparse.ArgumentParser(description="A2F-3D PoC: Audio -> BlendShapes")
    parser.add_argument("audio", help="Input WAV file (16-bit PCM mono)")
    parser.add_argument("-o", "--output", default="blendshapes.json", help="Output JSON")
    parser.add_argument("--fps", type=int, default=30, help="Target FPS")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dummy", action="store_true", help="Generate synthetic data")
    mode.add_argument("--a2f", action="store_true", help="Use local A2F-3D Docker service")

    parser.add_argument("--host", default="localhost:52000", help="A2F gRPC host:port")

    args = parser.parse_args()

    if args.dummy:
        run_dummy(args.audio, args.output, args.fps)
    elif args.a2f:
        asyncio.run(run_a2f(args.audio, args.output, args.host))


if __name__ == "__main__":
    main()
