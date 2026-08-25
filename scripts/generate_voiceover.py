import asyncio
import os
import subprocess

import edge_tts

# Segments with exact start timestamps (seconds) and spoken text
SEGMENTS = [
    {
        "start": 1.5,
        "text": "A robotic camera dolly halts during Scene 42 Take 3. In virtual production, a paused stage burns over twenty-five thousand dollars per hour.",
    },
    {
        "start": 15.0,
        "text": "Looking at the live stage telemetry: camera frame rate has collapsed to 16.2 frames per second, with seven navigation recovery loops and localization confidence dropping to 42%.",
    },
    {
        "start": 24.5,
        "text": "Re-running the CineOps Guardian agent live. Every tool call and reasoning step is streamed in real time over Server-Sent Events.",
    },
    {
        "start": 33.5,
        "text": "The agent actively investigates across Grafana MCP, Loki logs, Google Cloud BigQuery, and Foxglove MCAP telemetry before prompting Gemini 3.7 Flash.",
    },
    {
        "start": 43.0,
        "text": "Here is the fully auditable trace: eleven steps, each with its exact query parameters, retrieved evidence, and millisecond execution timing.",
    },
    {
        "start": 52.0,
        "text": "Gemini 3.7 Flash, with High Thinking level, evaluates three physical hypotheses and systematically rules two out.",
    },
    {
        "start": 61.0,
        "text": "The primary root cause is identified with 88% confidence: stale LiDAR to camera static transform extrinsics following a 35-millimeter prime lens swap.",
    },
    {
        "start": 68.5,
        "text": "Network congestion and GPU thermal throttling are rejected against empirical telemetry evidence, not guessed.",
    },
    {
        "start": 76.0,
        "text": "Comparing the LiDAR costmap against optical tracking, a plus 35-millimeter Z-extrinsic offset is localized directly from the raw Foxglove MCAP recording.",
    },
    {
        "start": 84.0,
        "text": "Live PromQL timeseries are pulled directly through the official Grafana MCP server.",
    },
    {
        "start": 91.0,
        "text": "Loki LogQL streams confirm the static transform checksum mismatch: CRC 0x8F4A expected versus 0x3E12 active.",
    },
    {
        "start": 97.0,
        "text": "Foxglove MCAP telemetry is cross-referenced with BigQuery, matching a prior stage incident with 94% similarity.",
    },
    {
        "start": 104.0,
        "text": "Crucially, the agent never moves the robot on its own. The recovery action pauses strictly at a human safety authorization gate.",
    },
    {
        "start": 111.0,
        "text": "The stage operator signs off on the calibration reload profile, with an explicit rollback procedure. Zero unverified robot actuation.",
    },
    {
        "start": 116.0,
        "text": "Recovery is verified automatically: static transform checksum converges, and full 24.00 frames per second genlock sync is restored.",
    },
]

VOICE = "en-US-AndrewMultilingualNeural"  # Professional, crisp, authentic narrator voice


async def generate_audio_clips():
    os.makedirs("scratch/voiceover", exist_ok=True)
    clips = []
    for idx, seg in enumerate(SEGMENTS):
        out_file = f"scratch/voiceover/seg_{idx:02d}.mp3"
        print(f"Generating clip {idx + 1}/{len(SEGMENTS)}: {seg['text'][:40]}...")
        communicate = edge_tts.Communicate(seg["text"], VOICE, rate="+3%")
        await communicate.save(out_file)

        # Check duration
        proc = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                out_file,
            ],
            capture_output=True,
            text=True,
        )
        dur = float(proc.stdout.strip() or "0")
        clips.append(
            {"idx": idx, "file": out_file, "start": seg["start"], "dur": dur, "text": seg["text"]}
        )
        print(f"  -> Generated {dur:.2f}s audio at start={seg['start']}s")
    return clips


if __name__ == "__main__":
    asyncio.run(generate_audio_clips())
