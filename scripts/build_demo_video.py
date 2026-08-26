#!/usr/bin/env python3
"""Builds the CineOps Guardian demo video: narration first, then picture.

The earlier pass picked scene start times by hand and generated narration
afterwards, so 11 of 15 clips talked over the next one and the last line ran past
the end of the video. This script inverts the dependency:

1. Synthesize each narration line and measure its real duration.
2. Drive the screen recording from those durations, so a scene is held on screen
   for exactly as long as its line takes to speak (plus a breath).
3. Record the wall-clock offset at which each scene actually started.
4. Mix each clip in at its recorded offset, so audio and picture cannot drift.

Usage:
    python scripts/build_demo_video.py            # full build
    python scripts/build_demo_video.py --audio    # narration only (fast check)
"""

import argparse
import asyncio
import json
import os
import subprocess
import sys

VOICE = "en-US-AndrewMultilingualNeural"
RATE = "+3%"
BREATH = 0.9  # seconds of silence held after a line before the next scene
MIN_HOLD = 3.0

OUT_DIR = "scratch/demo"
CLIP_DIR = f"{OUT_DIR}/narration"

# Each scene: an id, the on-screen caption, the narration, and the UI action the
# recorder performs while the line plays.
SCENES: list[dict[str, str]] = [
    {
        "id": "title",
        "caption": "",
        "action": "title_card",
        "text": (
            "A robotic camera dolly halts during Scene 42, Take 3. An idle virtual "
            "production stage burns about twenty-five thousand dollars an hour."
        ),
    },
    {
        "id": "incident",
        "caption": "Stage A halted — <b>Scene 42 Take 3</b>, burning <b>$25,000/hr</b>",
        "action": "show_header",
        "text": (
            "CineOps Guardian picks up the alert and opens a P1 incident against the "
            "dolly."
        ),
    },
    {
        "id": "telemetry",
        "caption": "Frame rate <b>16.2 fps</b> · <b>7</b> recovery loops · localization <b>42%</b>",
        "action": "show_metrics",
        "text": (
            "The telemetry is bad: sixteen point two frames per second, seven "
            "navigation recovery loops, localization confidence at forty-two percent."
        ),
    },
    {
        "id": "mcp",
        "caption": "Two <b>MCP servers</b>: official grafana/mcp-grafana + first-party CineOps",
        "action": "rerun_agent",
        "text": (
            "Watch it run. It connects to two Model Context Protocol servers: Grafana's "
            "own mcp-grafana binary, and a CineOps server for Foxglove, BigQuery, Cloud "
            "Storage and the MCAP inspector."
        ),
    },
    {
        "id": "agentic",
        "caption": "<b>Gemini 3.7 Flash</b> chooses every tool call — nothing is scripted",
        "action": "follow_trace",
        "text": (
            "Nothing here is a fixed pipeline. Gemini three point seven Flash gets the "
            "tool catalogue and decides what to call. This trace is its own decision log."
        ),
    },
    {
        "id": "discovery",
        "caption": "Agent discovers datasource UIDs, then queries <b>PromQL</b> and <b>LogQL</b>",
        "action": "follow_trace",
        "text": (
            "It lists the Grafana datasources rather than assuming their identifiers, "
            "then queries Prometheus and Loki through the Grafana MCP server."
        ),
    },
    {
        "id": "measure",
        "caption": "MCAP inspected before any spatial claim — <b>+35mm Z offset</b> measured",
        "action": "follow_trace",
        "text": (
            "Before claiming a physical cause it measures the offset itself: plus "
            "thirty-five millimetres on the Z axis, camera frame to LiDAR."
        ),
    },
    {
        "id": "vision",
        "caption": "Then it <b>renders the telemetry and looks at it</b> — MCP image content",
        "action": "follow_trace",
        "text": (
            "Then it renders the telemetry and looks at the frame. In its own words, the "
            "path breaks from a straight line into tight zig-zag loops around a phantom "
            "obstacle."
        ),
    },
    {
        "id": "ordering",
        "caption": "The frame states the <b>order of events</b> — cause precedes symptom",
        "action": "follow_trace",
        "text": (
            "The frame also carries the order of events, which separates cause from "
            "symptom. The transform diverges at ten seconds. The frame rate falls at "
            "twelve."
        ),
    },
    {
        "id": "baseline",
        "caption": "<b>Compared against a clean take</b> — identical means not the cause",
        "action": "follow_trace",
        "text": (
            "It compares the failing take against a clean run of the same rig. Anything "
            "identical in both is normal for this rig, and cannot be the cause."
        ),
    },
    {
        "id": "ablation",
        "caption": "Ablation: give it a baseline that <b>matches</b> — it withdraws the claim",
        "action": "follow_trace",
        "text": (
            "We tested that this binds. Give it a baseline whose transform matches the "
            "failing take, and it drops its own root cause from ninety-eight percent to "
            "thirty. If it ignores the baseline, a guardrail catches it."
        ),
    },
    {
        "id": "history",
        "caption": "<b>BigQuery</b> history: a prior take failed the same way",
        "action": "follow_trace",
        "text": (
            "BigQuery history shows this has happened before, and what fixed it."
        ),
    },
    {
        "id": "foxglove",
        "caption": "Agent publishes the bag to <b>Foxglove</b> itself",
        "action": "follow_trace",
        "text": (
            "It preserves the evidence itself, and hands the operator a Foxglove link "
            "that opens at the annotated moment rather than a file listing."
        ),
    },
    {
        "id": "hypotheses",
        "caption": "Ranked hypotheses — alternatives <b>rejected against telemetry</b>",
        "action": "show_hypotheses",
        "text": (
            "Only then does it commit: stale LiDAR to camera calibration after the lens "
            "swap. The alternatives are not dismissed by assertion — they are rejected "
            "against the telemetry it pulled."
        ),
    },
    {
        "id": "gate",
        "caption": "Recovery stops at a <b>human safety gate</b> — zero robot actuation",
        "action": "open_gate",
        "text": (
            "Recovery stops at a human safety gate. The agent has no tool that can move "
            "the robot. An operator reviews the reload and the rollback, and signs off."
        ),
    },
    {
        "id": "recovered",
        "caption": "Verified: TF checksum converged, <b>24.00 fps genlock restored</b>",
        "action": "authorize",
        "text": (
            "Recovery is then verified automatically: the checksum converges and "
            "twenty-four frame per second genlock returns. The take is saved."
        ),
    },
    {
        "id": "close",
        "caption": "",
        "action": "close_card",
        "text": (
            "From alert to verified recovery, every tool call over MCP. Open source "
            "under Apache two point zero."
        ),
    },
]


def ffprobe_duration(path: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", path],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out or 0.0)


async def synthesize() -> list[dict]:
    import edge_tts

    os.makedirs(CLIP_DIR, exist_ok=True)
    plan: list[dict] = []
    for index, scene in enumerate(SCENES):
        path = f"{CLIP_DIR}/{index:02d}_{scene['id']}.mp3"
        await edge_tts.Communicate(scene["text"], VOICE, rate=RATE).save(path)
        duration = ffprobe_duration(path)
        hold = max(duration + BREATH, MIN_HOLD)
        plan.append({
            "index": index,
            "id": scene["id"],
            "caption": scene["caption"],
            "action": scene["action"],
            "clip": path,
            "narration_seconds": round(duration, 3),
            "hold_seconds": round(hold, 3),
        })
        print(f"  [{index:02}] {scene['id']:<11} narration {duration:6.2f}s  hold {hold:6.2f}s")
    total = sum(p["hold_seconds"] for p in plan)
    print(f"\n  narration total {sum(p['narration_seconds'] for p in plan):.1f}s"
          f" -> video {total:.1f}s ({total / 60:.2f} min)")
    if total > 175:
        print("  WARNING: exceeds a comfortable 3-minute limit; trim narration.", file=sys.stderr)
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(f"{OUT_DIR}/plan.json", "w") as handle:
        json.dump(plan, handle, indent=1)
    return plan


def mix(plan_path: str, video_path: str, out_path: str) -> None:
    """Overlays each narration clip at the scene offset the recorder measured."""
    with open(plan_path) as handle:
        plan = json.load(handle)
    offsets = [p for p in plan if p.get("actual_start_seconds") is not None]
    if not offsets:
        raise SystemExit("plan.json has no actual_start_seconds; run the recorder first")

    inputs: list[str] = ["-i", video_path]
    filters: list[str] = []
    labels: list[str] = []
    for slot, item in enumerate(offsets, start=1):
        inputs += ["-i", item["clip"]]
        delay_ms = int(item["actual_start_seconds"] * 1000)
        filters.append(f"[{slot}:a]adelay={delay_ms}|{delay_ms},aresample=48000[a{slot}]")
        labels.append(f"[a{slot}]")
    filters.append(
        "".join(labels) + f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0[mixed]"
    )
    filter_complex = ";".join(filters)

    cmd = [
        "ffmpeg", "-v", "error", *inputs,
        "-filter_complex", filter_complex,
        "-map", "0:v:0", "-map", "[mixed]",
        "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-pix_fmt", "yuv420p", "-r", "30",
        "-movflags", "+faststart", "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_path, "-y",
    ]
    subprocess.run(cmd, check=True)
    print(f"mixed -> {out_path} ({ffprobe_duration(out_path):.2f}s)")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audio", action="store_true", help="synthesize narration only")
    parser.add_argument("--mix", nargs=3, metavar=("PLAN", "VIDEO", "OUT"),
                        help="mix narration into a recorded video")
    args = parser.parse_args()

    if args.mix:
        mix(*args.mix)
        return
    asyncio.run(synthesize())
    if not args.audio:
        print("\nNarration ready. Now run the recorder, then re-run with --mix.")


if __name__ == "__main__":
    main()
