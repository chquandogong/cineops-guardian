import os
import shutil
import subprocess

# Timeline in seconds
SEGMENTS = [
    {"file": "scratch/voiceover/seg_00.mp3", "start_ms": 1500},
    {"file": "scratch/voiceover/seg_01.mp3", "start_ms": 15000},
    {"file": "scratch/voiceover/seg_02.mp3", "start_ms": 25000},
    {"file": "scratch/voiceover/seg_03.mp3", "start_ms": 34000},
    {"file": "scratch/voiceover/seg_04.mp3", "start_ms": 43500},
    {"file": "scratch/voiceover/seg_05.mp3", "start_ms": 52500},
    {"file": "scratch/voiceover/seg_06.mp3", "start_ms": 61500},
    {"file": "scratch/voiceover/seg_07.mp3", "start_ms": 69000},
    {"file": "scratch/voiceover/seg_08.mp3", "start_ms": 76500},
    {"file": "scratch/voiceover/seg_09.mp3", "start_ms": 84500},
    {"file": "scratch/voiceover/seg_10.mp3", "start_ms": 91000},
    {"file": "scratch/voiceover/seg_11.mp3", "start_ms": 97500},
    {"file": "scratch/voiceover/seg_12.mp3", "start_ms": 104500},
    {"file": "scratch/voiceover/seg_13.mp3", "start_ms": 111500},
    {"file": "scratch/voiceover/seg_14.mp3", "start_ms": 116500},
]

# Total video duration is 122.133s
TOTAL_DURATION_MS = 122133

inputs = []
filter_complex_parts = []
mix_labels = []

for idx, s in enumerate(SEGMENTS):
    inputs.extend(["-i", s["file"]])
    filter_complex_parts.append(f"[{idx}:a]adelay={s['start_ms']}|{s['start_ms']}[a{idx}]")
    mix_labels.append(f"[a{idx}]")

filter_complex_str = (
    ";".join(filter_complex_parts)
    + ";"
    + "".join(mix_labels)
    + f"amix=inputs={len(SEGMENTS)}:dropout_transition=0:normalize=0,volume=1.8[aout]"
)

out_audio = "scratch/voiceover_master.wav"

cmd_audio = (
    ["ffmpeg", "-y"]
    + inputs
    + [
        "-filter_complex",
        filter_complex_str,
        "-map",
        "[aout]",
        "-ac",
        "2",
        "-ar",
        "48000",
        "-t",
        "122.133",
        out_audio,
    ]
)
print("Building master audio timeline...")
subprocess.run(cmd_audio, check=True)

# Now Mux with the video
original_video = "/home/chquan/CineOps-Guardian-Demo.mp4"
backup_video = "/home/chquan/CineOps-Guardian-Demo-Original.mp4"
dubbed_video = "/home/chquan/CineOps-Guardian-Demo-Dubbed.mp4"

if not os.path.exists(backup_video):
    import shutil

    shutil.copyfile(original_video, backup_video)
    print(f"Backed up original video to {backup_video}")

cmd_mux = [
    "ffmpeg",
    "-y",
    "-i",
    original_video,
    "-i",
    out_audio,
    "-c:v",
    "copy",
    "-c:a",
    "aac",
    "-b:a",
    "192k",
    "-map",
    "0:v:0",
    "-map",
    "1:a:0",
    "-shortest",
    dubbed_video,
]
print("Muxing video with new neural voiceover...")
subprocess.run(cmd_mux, check=True)

shutil.copyfile(dubbed_video, original_video)
print(f"Updated {original_video} with high-quality English voiceover narration!")
