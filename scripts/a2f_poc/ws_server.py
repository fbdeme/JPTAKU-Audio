"""
WebSocket server that streams BlendShape data to Flutter clients at 30fps.

Two modes:
  --file   : Replay from a pre-generated blendshapes.json (for testing)
  --live   : Connect to A2F-3D Docker, process audio, and stream in real-time

Usage:
  uv run python ws_server.py --file blendshapes.json --port 8765
  uv run python ws_server.py --live --audio ../../assets/reference_voice/tsumugi/tsumugi_04.wav --port 8765
"""

import argparse
import asyncio
import json
import time

import websockets


async def stream_from_file(websocket, filepath: str, loop: bool = True):
    """Replay BlendShape frames from a JSON file at original FPS."""
    with open(filepath) as f:
        data = json.load(f)

    fps = data.get("fps", 30)
    frames = data["frames"]
    frame_interval = 1.0 / fps

    print(f"Client connected: {websocket.remote_address}")
    print(f"Streaming {len(frames)} frames at {fps}fps from {filepath}")

    # Send metadata first
    await websocket.send(json.dumps({
        "type": "metadata",
        "fps": fps,
        "n_frames": len(frames),
        "duration": data.get("duration", len(frames) / fps),
        "blendshape_names": list(data.get("anime_relevant", data.get("blendshape_names", []))),
    }))

    while True:
        start_time = time.monotonic()

        for i, frame in enumerate(frames):
            frame_start = time.monotonic()

            msg = json.dumps({
                "type": "frame",
                "index": i,
                "time": frame["time"],
                "blendshapes": frame["blendshapes"],
            })

            try:
                await websocket.send(msg)
            except websockets.ConnectionClosed:
                print("Client disconnected")
                return

            # Sleep to maintain target FPS
            elapsed = time.monotonic() - frame_start
            sleep_time = frame_interval - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)

        # Send end marker
        await websocket.send(json.dumps({"type": "end"}))

        if not loop:
            break

        # Small pause before looping
        await asyncio.sleep(0.5)

    total = time.monotonic() - start_time
    print(f"Streamed {len(frames)} frames in {total:.2f}s (target: {len(frames)/fps:.2f}s)")


async def serve(handler, port: int):
    """Start the WebSocket server."""
    print(f"WebSocket server listening on ws://0.0.0.0:{port}")
    async with websockets.serve(handler, "0.0.0.0", port):
        await asyncio.Future()  # run forever


def main():
    parser = argparse.ArgumentParser(description="BlendShape WebSocket Server")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--no-loop", action="store_true", help="Don't loop the animation")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--file", help="Replay from blendshapes.json file")
    mode.add_argument("--live", action="store_true", help="Live A2F processing (TODO)")

    parser.add_argument("--audio", help="Audio file for --live mode")

    args = parser.parse_args()

    if args.file:
        handler = lambda ws: stream_from_file(ws, args.file, loop=not args.no_loop)
        asyncio.run(serve(handler, args.port))
    elif args.live:
        print("Live mode not yet implemented. Use --file with pre-generated data.")


if __name__ == "__main__":
    main()
