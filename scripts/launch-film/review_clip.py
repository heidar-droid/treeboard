#!/usr/bin/env python3
"""Extract key frames + audio sample from a Kling video clip for AI review.

Usage: review_clip.py <video_path>

Produces 5 PNG frames (start, 25%, 50%, 75%, end) + extracts audio as WAV.
"""
import subprocess
import sys
from pathlib import Path
import imageio_ffmpeg

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


def probe_duration(video: Path) -> float:
    """Get video duration in seconds via ffmpeg stderr parsing."""
    result = subprocess.run(
        [FFMPEG, "-i", str(video)],
        capture_output=True,
        text=True,
    )
    for line in result.stderr.splitlines():
        if "Duration" in line:
            # "  Duration: 00:00:06.04, start: 0.000000, bitrate: ..."
            time_str = line.split("Duration: ")[1].split(",")[0]
            h, m, s = time_str.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    raise RuntimeError(f"Could not parse duration from ffmpeg output")


def extract_frame(video: Path, timestamp: float, out: Path) -> None:
    subprocess.run(
        [
            FFMPEG, "-y", "-ss", f"{timestamp}", "-i", str(video),
            "-frames:v", "1", "-q:v", "2", str(out),
        ],
        capture_output=True,
        check=True,
    )


def extract_audio(video: Path, out: Path) -> None:
    subprocess.run(
        [
            FFMPEG, "-y", "-i", str(video),
            "-vn", "-acodec", "pcm_s16le", "-ar", "44100", str(out),
        ],
        capture_output=True,
        check=True,
    )


def main() -> None:
    video = Path(sys.argv[1])
    if not video.exists():
        raise FileNotFoundError(video)

    review_dir = Path("/tmp") / f"review-{video.stem}"
    review_dir.mkdir(parents=True, exist_ok=True)

    dur = probe_duration(video)
    print(f"Video: {video.name}  duration: {dur:.2f}s")

    timestamps = {
        "00-start": 0.05,
        "25-quarter": dur * 0.25,
        "50-mid": dur * 0.50,
        "75-three-quarter": dur * 0.75,
        "99-end": max(dur - 0.1, 0.1),
    }

    for label, ts in timestamps.items():
        out = review_dir / f"{label}.png"
        extract_frame(video, ts, out)
        print(f"  frame @ {ts:.2f}s → {out}")

    audio_out = review_dir / "audio.wav"
    extract_audio(video, audio_out)
    print(f"  audio → {audio_out}")

    print(f"\nReview directory: {review_dir}")


if __name__ == "__main__":
    main()
