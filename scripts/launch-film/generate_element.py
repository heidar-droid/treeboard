#!/usr/bin/env python3
"""Generate a Nano Banana image via Kie.ai and download it.

Usage: generate_element.py <output_path> <prompt>
"""
import json
import os
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
    raise RuntimeError("KIE_API_KEY not found in workspace .env")


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
    prompt = sys.argv[2]

    print(f"→ Submitting Nano Banana task")
    print(f"  Output: {output_path}")
    print(f"  Prompt: {prompt[:120]}...")

    response = kie_post(
        "/jobs/createTask",
        {
            "model": "google/nano-banana",
            "input": {
                "prompt": prompt,
                "aspect_ratio": "16:9",
                "output_format": "png",
            },
        },
    )
    print(f"  Response: {json.dumps(response)[:200]}")

    if response.get("code") != 200:
        raise RuntimeError(f"Submit failed: {response}")

    task_id = response["data"]["taskId"]
    print(f"  Task ID: {task_id}")

    print(f"→ Polling (Nano Banana typically takes 20-60s)")
    for attempt in range(30):
        time.sleep(8)
        status = kie_get(f"/jobs/recordInfo?taskId={task_id}")
        if status.get("code") != 200:
            print(f"  Status check error: {status}")
            continue
        state = status["data"].get("state")
        print(f"  [{attempt + 1}] state: {state}")
        if state == "success":
            result_json = status["data"].get("resultJson")
            if isinstance(result_json, str):
                result_json = json.loads(result_json)
            urls = result_json.get("resultUrls", [])
            if not urls:
                raise RuntimeError(f"No result URLs in success: {status}")
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

    raise RuntimeError("Timed out after 4 minutes")


if __name__ == "__main__":
    main()
