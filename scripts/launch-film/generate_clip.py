#!/usr/bin/env python3
"""Generate a Kling 3.0 video clip via Kie.ai with native audio.

Usage:
  generate_clip.py <output_path> <duration> <mode> <prompt> [image_url] [element_urls...]

  duration: 3-15 (seconds)
  mode: std | pro | 4K
  image_url: optional first-frame image for image-to-video
  element_urls: optional Kling Elements references (paired name=url, comma-separated)

Example:
  generate_clip.py clips/clip-01.mp4 6 pro "..." https://files.catbox.moe/x.png
"""
import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def load_kie_key() -> str:
    env_path = Path("/Users/smb/Infinivo AI Workspace/.env")
    for line in env_path.read_text().splitlines():
        if line.startswith("KIE_API_KEY="):
            return line.split("=", 1)[1].strip()
    raise RuntimeError("KIE_API_KEY not found")


KIE_BASE = "https://api.kie.ai/api/v1"
KEY = load_kie_key()
HEADERS = {
    "Authorization": f"Bearer {KEY}",
    "Content-Type": "application/json",
}


def kie_post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{KIE_BASE}{path}",
        data=json.dumps(body).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def kie_get(path: str) -> dict:
    req = urllib.request.Request(f"{KIE_BASE}{path}", headers=HEADERS, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main() -> None:
    output_path = Path(sys.argv[1])
    duration = sys.argv[2]
    mode = sys.argv[3]
    prompt = sys.argv[4]
    image_url = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None

    input_obj = {
        "prompt": prompt,
        "sound": True,
        "duration": duration,
        "aspect_ratio": "16:9",
        "mode": mode,
        "multi_shots": False,
    }
    if image_url:
        input_obj["image_urls"] = [image_url]

    body = {"model": "kling-3.0/video", "input": input_obj}

    print(f"→ Submitting Kling 3.0 task ({mode}, {duration}s)")
    print(f"  Output: {output_path}")
    if image_url:
        print(f"  Image-to-video from: {image_url}")
    print(f"  Prompt: {prompt[:150]}...")

    response = kie_post("/jobs/createTask", body)
    print(f"  Response: {json.dumps(response)[:200]}")

    if response.get("code") != 200:
        raise RuntimeError(f"Submit failed: {response}")

    task_id = response["data"]["taskId"]
    print(f"  Task ID: {task_id}")

    print(f"→ Polling (Kling 3.0 typically takes 2-6 minutes)")
    for attempt in range(36):
        time.sleep(20)
        status = kie_get(f"/jobs/recordInfo?taskId={task_id}")
        if status.get("code") != 200:
            print(f"  [{attempt + 1}] status check error: {status}")
            continue
        state = status["data"].get("state")
        print(f"  [{attempt + 1}] state: {state}")
        if state == "success":
            result_json = status["data"].get("resultJson")
            if isinstance(result_json, str):
                result_json = json.loads(result_json)
            urls = result_json.get("resultUrls", [])
            if not urls:
                raise RuntimeError(f"No result URLs: {status}")
            url = urls[0]
            print(f"→ Downloading: {url}")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            subprocess.run(
                ["/usr/bin/curl", "-sL", "-A", "Mozilla/5.0", url, "-o", str(output_path)],
                check=True,
            )
            size = output_path.stat().st_size
            print(f"→ Saved: {output_path} ({size:,} bytes)")
            return
        if state == "fail":
            raise RuntimeError(f"Generation failed: {status}")

    raise RuntimeError("Timed out after 12 minutes")


if __name__ == "__main__":
    main()
