#!/usr/bin/env python3
"""Generate a Seedance 2 Fast video clip via Kie.ai with native audio.

Usage:
  generate_clip_seedance.py <output_path> <duration> <prompt> [first_frame_url] [last_frame_url]

  duration: 4-15 seconds
  first_frame_url: optional starting frame (image-to-video)
  last_frame_url: optional ending frame (use this for "materializes TO X" shots)
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
    duration = int(sys.argv[2])
    prompt = sys.argv[3]
    first_frame_url = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
    last_frame_url = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None

    input_obj = {
        "prompt": prompt,
        "duration": duration,
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "generate_audio": True,
    }
    if first_frame_url:
        input_obj["first_frame_url"] = first_frame_url
    if last_frame_url:
        input_obj["last_frame_url"] = last_frame_url

    body = {"model": "bytedance/seedance-2-fast", "input": input_obj}

    print(f"→ Submitting Seedance 2 Fast task ({duration}s, 720p)")
    print(f"  Output: {output_path}")
    if first_frame_url:
        print(f"  First frame: {first_frame_url}")
    if last_frame_url:
        print(f"  Last frame: {last_frame_url}")
    print(f"  Prompt: {prompt[:150]}...")

    response = kie_post("/jobs/createTask", body)
    print(f"  Response: {json.dumps(response)[:200]}")

    if response.get("code") != 200:
        raise RuntimeError(f"Submit failed: {response}")

    task_id = response["data"]["taskId"]
    print(f"  Task ID: {task_id}")

    print(f"→ Polling (Seedance Fast typically takes 1-3 minutes)")
    for attempt in range(30):
        time.sleep(15)
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

    raise RuntimeError("Timed out after 7.5 minutes")


if __name__ == "__main__":
    main()
