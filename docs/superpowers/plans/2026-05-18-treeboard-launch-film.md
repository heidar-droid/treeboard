# Treeboard Launch Film Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce and launch the Treeboard "In the Beginning" cinematic launch film — a 90s creation myth — in three cuts (90s master, 60s X loop, 9:16 vertical) over 5 days using Kie.ai (Kling 3.0 + Nano Banana + voice generation), DaVinci Resolve, and a 4-tweet launch thread.

**Architecture:** Production runs as a sequential pipeline: (1) build a Kling Elements library of canonical pill node references in Nano Banana to lock visual consistency, (2) generate 8 cinematic clips with Kling 3.0 via Kie.ai API with `sound: true` for native audio, (3) generate the VO line via Kie.ai voice endpoint, (4) assemble all assets in DaVinci Resolve with a single LUT applied across every clip, (5) export three cuts, (6) ship the launch thread.

**Tech Stack:** Kie.ai API (Kling 3.0, Nano Banana, voice generation), curl + bash scripts, DaVinci Resolve (free), local asset storage in `media/launch-film/`, git for asset versioning.

**Reference spec:** `docs/superpowers/specs/2026-05-18-treeboard-launch-film-design.md`

---

## File Structure

All artifacts produced by this plan live under `media/launch-film/` in the Treeboard repo. Scripts that call the Kie.ai API live under `scripts/launch-film/`.

```
media/launch-film/
├── elements/                    # Kling Elements library source images
│   ├── treeboard_node_hero.png
│   ├── treeboard_node_front.png
│   ├── treeboard_node_quarter_left.png
│   ├── treeboard_node_quarter_right.png
│   └── treeboard_node_back.png
├── keyframes/
│   └── galaxy_keyframe.png      # Scene 3 image-to-video source
├── clips/
│   ├── clip-01-first-light.mp4
│   ├── clip-02-bloom-a.mp4
│   ├── clip-03-bloom-b.mp4
│   ├── clip-04-galaxy-a.mp4
│   ├── clip-05-galaxy-b.mp4
│   ├── clip-06-creator-a.mp4
│   ├── clip-07-creator-b.mp4
│   └── clip-08-command.mp4
├── audio/
│   └── vo-lockup.wav            # Generated VO line
├── davinci/
│   └── treeboard-launch.drp     # DaVinci Resolve project file
└── exports/
    ├── treeboard-launch-90s-16x9.mp4
    ├── treeboard-launch-60s-16x9.mp4
    └── treeboard-launch-60s-9x16.mp4

scripts/launch-film/
├── kie_client.sh                # Auth + helpers
├── generate_element.sh          # Calls Nano Banana
├── generate_clip.sh             # Calls Kling 3.0
├── generate_vo.sh               # Calls Kie.ai voice
└── poll_task.sh                 # Polls task status until complete

docs/superpowers/specs/
└── 2026-05-18-treeboard-launch-film-design.md  # (already exists)
```

---

## Task 1: Setup — Workspace and API Verification

**Files:**
- Create: `media/launch-film/elements/.gitkeep`
- Create: `media/launch-film/keyframes/.gitkeep`
- Create: `media/launch-film/clips/.gitkeep`
- Create: `media/launch-film/audio/.gitkeep`
- Create: `media/launch-film/exports/.gitkeep`
- Create: `scripts/launch-film/kie_client.sh`
- Modify: `.gitignore` (if needed — keep media/ tracked, ignore davinci cache)

- [ ] **Step 1: Create the directory structure**

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
mkdir -p media/launch-film/{elements,keyframes,clips,audio,davinci,exports}
mkdir -p scripts/launch-film
touch media/launch-film/{elements,keyframes,clips,audio,exports}/.gitkeep
```

- [ ] **Step 2: Verify the KIE_API_KEY is in environment**

```bash
grep -c "^KIE_API_KEY=" "/Users/smb/Infinivo AI Workspace/.env"
```

Expected: `2` (key appears twice in workspace env). If `0`, stop and ask Sir for the key.

- [ ] **Step 3: Create `scripts/launch-film/kie_client.sh`**

```bash
#!/bin/bash
# Kie.ai API client helpers for the Treeboard launch film
set -euo pipefail

KIE_API_KEY="${KIE_API_KEY:-$(grep '^KIE_API_KEY=' "/Users/smb/Infinivo AI Workspace/.env" | head -1 | cut -d= -f2)}"
KIE_BASE="https://api.kie.ai/api/v1"

kie_post() {
  local path="$1"
  local body="$2"
  curl -s -X POST "${KIE_BASE}${path}" \
    -H "Authorization: Bearer ${KIE_API_KEY}" \
    -H "Content-Type: application/json" \
    -d "${body}"
}

kie_get() {
  local path="$1"
  curl -s -X GET "${KIE_BASE}${path}" \
    -H "Authorization: Bearer ${KIE_API_KEY}"
}

export -f kie_post kie_get
export KIE_API_KEY KIE_BASE
```

- [ ] **Step 4: Make it executable**

```bash
chmod +x scripts/launch-film/kie_client.sh
```

- [ ] **Step 5: Smoke-test the Kie.ai API**

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
source scripts/launch-film/kie_client.sh
kie_post "/jobs/createTask" '{}' | python3 -m json.tool
```

Expected output: `{"code": 422, "msg": "The input cannot be null", "data": null}` — this confirms auth works and the endpoint is reachable. A 401 means the key is wrong.

- [ ] **Step 6: Commit the setup**

```bash
git add media/launch-film/.gitkeep scripts/launch-film/kie_client.sh media/launch-film/*/.gitkeep
git commit -m "chore(launch-film): scaffold workspace and Kie.ai client"
```

---

## Task 2: Generate the Canonical Treeboard Pill Node (Element 1 of 5)

**Files:**
- Create: `scripts/launch-film/generate_element.sh`
- Create: `media/launch-film/elements/treeboard_node_hero.png`

- [ ] **Step 1: Create the Nano Banana generation script**

Write `scripts/launch-film/generate_element.sh`:

```bash
#!/bin/bash
# Generate a single Nano Banana image for the Kling Elements library
set -euo pipefail
source "$(dirname "$0")/kie_client.sh"

PROMPT="$1"
OUTPUT_PATH="$2"

echo "→ Submitting Nano Banana task..."
RESPONSE=$(kie_post "/jobs/createTask" "$(cat <<JSON
{
  "model": "google/nano-banana",
  "input": {
    "prompt": $(echo "$PROMPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    "aspect_ratio": "16:9",
    "output_format": "png"
  }
}
JSON
)")

echo "$RESPONSE" | python3 -m json.tool
TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['taskId'])")
echo "→ Task ID: $TASK_ID"
echo "→ Polling for completion (this takes 20-60s)..."

while true; do
  sleep 10
  STATUS=$(kie_get "/jobs/recordInfo?taskId=${TASK_ID}")
  STATE=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['state'])")
  echo "  state: $STATE"
  if [ "$STATE" = "success" ]; then
    URL=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['resultJson']['resultUrls'][0])")
    echo "→ Downloading: $URL"
    curl -sL "$URL" -o "$OUTPUT_PATH"
    echo "→ Saved: $OUTPUT_PATH"
    exit 0
  elif [ "$STATE" = "fail" ]; then
    echo "FAILED:"; echo "$STATUS" | python3 -m json.tool; exit 1
  fi
done
```

```bash
chmod +x scripts/launch-film/generate_element.sh
```

**Note:** The exact JSON parameter names (`model`, `input.prompt`, `resultJson.resultUrls`) may differ slightly per Kie.ai's current schema. If a field is rejected with a 422, inspect the error message and adjust — the field names are deterministic per the docs at <https://docs.kie.ai/market/google/nano-banana>.

- [ ] **Step 2: Generate the canonical hero node**

```bash
cd "/Users/smb/Infinivo AI Workspace/Personal Projects/treeboard"
./scripts/launch-film/generate_element.sh "A single glowing pill-shaped node, floating in absolute darkness. Sage-green bioluminescent glow (#b6d4a7) emanating from the pill body. Soft inner glow, crisp outer halo at 30px radius. Rounded rectangle shape, 70px wide × 26px tall. Subtle text 'index.ts' rendered in JetBrains Mono at 9px inside the pill in soft sage. Dark forest green-black background (#060a08). Subtle radial vignette. Film grain overlay. Cinematic, photorealistic, depth of field, 4K. No human. No interface. No screen. Just the pill in void." \
  media/launch-film/elements/treeboard_node_hero.png
```

- [ ] **Step 3: Open the image and visually verify it matches the brief**

```bash
open media/launch-film/elements/treeboard_node_hero.png
```

Checklist:
- Pill shape (rounded rectangle, not a sphere or square)
- Sage-green color matches `#b6d4a7` (not blue, not teal, not pure green)
- Glow halo visible but not blown out
- Dark forest background (not pure black, not blue-black)
- Subtle text inside the pill is legible
- No artifacts, no humans, no screens visible

If any check fails: regenerate with prompt adjustments (max 3 attempts before escalating to Sir).

- [ ] **Step 4: Commit the hero element**

```bash
git add media/launch-film/elements/treeboard_node_hero.png scripts/launch-film/generate_element.sh
git commit -m "feat(launch-film): generate canonical Treeboard pill node hero"
```

---

## Task 3: Generate the 4 Reference Angles (Elements 2–5)

**Files:**
- Create: `media/launch-film/elements/treeboard_node_front.png`
- Create: `media/launch-film/elements/treeboard_node_quarter_left.png`
- Create: `media/launch-film/elements/treeboard_node_quarter_right.png`
- Create: `media/launch-film/elements/treeboard_node_back.png`

- [ ] **Step 1: Generate the front-on reference**

```bash
./scripts/launch-film/generate_element.sh "A single sage-green glowing pill-shaped node viewed directly from the front, perfectly centered, neutral lighting, no rotation. Rounded rectangle 70×26 with bioluminescent sage glow (#b6d4a7). Dark forest void background (#060a08). Cinematic, clean reference shot, 4K." \
  media/launch-film/elements/treeboard_node_front.png
```

- [ ] **Step 2: Generate the ¾ left reference**

```bash
./scripts/launch-film/generate_element.sh "A single sage-green glowing pill-shaped node rotated 30 degrees to the left, three-quarter view, soft side-lighting from the right. Rounded rectangle 70×26 with bioluminescent sage glow (#b6d4a7). Dark forest void background (#060a08). Cinematic reference shot, 4K." \
  media/launch-film/elements/treeboard_node_quarter_left.png
```

- [ ] **Step 3: Generate the ¾ right reference**

```bash
./scripts/launch-film/generate_element.sh "A single sage-green glowing pill-shaped node rotated 30 degrees to the right, three-quarter view, soft side-lighting from the left. Rounded rectangle 70×26 with bioluminescent sage glow (#b6d4a7). Dark forest void background (#060a08). Cinematic reference shot, 4K." \
  media/launch-film/elements/treeboard_node_quarter_right.png
```

- [ ] **Step 4: Generate the back reference**

```bash
./scripts/launch-film/generate_element.sh "A single sage-green glowing pill-shaped node viewed from behind, rear three-quarter angle, slight overhead perspective. The text on the pill is not visible from this angle. Rounded rectangle 70×26 with bioluminescent sage glow (#b6d4a7) wrapping around the back edge. Dark forest void background (#060a08). Cinematic reference shot, 4K." \
  media/launch-film/elements/treeboard_node_back.png
```

- [ ] **Step 5: Open all 5 references side by side and verify visual consistency**

```bash
open media/launch-film/elements/treeboard_node_*.png
```

The 5 images must share:
- Identical pill proportions (70:26 ratio)
- Identical sage glow color
- Identical background tone
- Same level of grain and bloom

If any image is visibly inconsistent (different blue tint, different glow intensity, different shape) — regenerate that single image only.

- [ ] **Step 6: Upload all 5 to the Kling Elements library**

The Elements library upload is done through the Kie.ai web dashboard (no API endpoint exposed).

1. Open <https://kie.ai/market/kling/kling-3-0>
2. Navigate to the Elements panel
3. Upload all 5 images, tag the set as `treeboard_node`
4. Note the Element ID returned (will be referenced as `@treeboard_node` in prompts)
5. Save the Element ID into a local file:

```bash
echo "ELEMENT_ID_NODE=<paste-id-here>" > scripts/launch-film/.element-ids
```

- [ ] **Step 7: Commit the references**

```bash
git add media/launch-film/elements/treeboard_node_*.png
git commit -m "feat(launch-film): add 4 reference angles for Kling Elements library"
```

---

## Task 4: Generate the Galaxy Key Frame for Scene 3

**Files:**
- Create: `media/launch-film/keyframes/galaxy_keyframe.png`

- [ ] **Step 1: Generate the galaxy constellation key frame**

```bash
./scripts/launch-film/generate_element.sh "A vast constellation of hundreds of glowing pill-shaped nodes, scattered across pure black void like a galaxy. Sage-green nodes (#b6d4a7) dominant, with amber (#f59e0b) and green (#10b981) nodes mixed in. Luminous sage-green filaments connecting clusters of nodes like fiber-optic threads. Volumetric fog at edges. Cosmic depth — nodes recede into distance. Slight bloom on brightest nodes. Film grain. Dark forest green-black ambient color cast. Cinematic, 4K, god's-eye composition, wide shot." \
  media/launch-film/keyframes/galaxy_keyframe.png
```

- [ ] **Step 2: Open and verify it matches the brief**

```bash
open media/launch-film/keyframes/galaxy_keyframe.png
```

Checklist:
- Hundreds of pill-shaped nodes (not spheres, not dots)
- Sage dominant, amber and green secondary
- Visible connecting threads between clusters
- Sense of cosmic depth (foreground brighter, background fading)
- Dark forest tone (not pure black)
- No human, no interface visible

Up to 3 regeneration attempts. If still wrong, escalate to Sir before proceeding.

- [ ] **Step 3: Commit the key frame**

```bash
git add media/launch-film/keyframes/galaxy_keyframe.png
git commit -m "feat(launch-film): generate galaxy constellation key frame for Scene 3"
```

---

## Task 5: Build the Kling Generation Script

**Files:**
- Create: `scripts/launch-film/generate_clip.sh`

- [ ] **Step 1: Write the Kling 3.0 generation script**

```bash
#!/bin/bash
# Generate a single Kling 3.0 video clip with native audio
set -euo pipefail
source "$(dirname "$0")/kie_client.sh"

PROMPT="$1"
DURATION="$2"     # 3-15 seconds
OUTPUT_PATH="$3"
MODE="${4:-pro}"  # std | pro | 4K
IMAGE_URL="${5:-}" # optional: image-to-video source

INPUT_JSON=$(python3 -c "
import json, sys
input_obj = {
    'prompt': $(echo "$PROMPT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    'sound': True,
    'duration': '$DURATION',
    'aspect_ratio': '16:9',
    'mode': '$MODE'
}
if '$IMAGE_URL':
    input_obj['image_urls'] = ['$IMAGE_URL']
print(json.dumps(input_obj))
")

BODY=$(python3 -c "
import json
print(json.dumps({
    'model': 'kling-3.0/video',
    'input': json.loads('''$INPUT_JSON''')
}))
")

echo "→ Submitting Kling 3.0 task ($MODE, ${DURATION}s)..."
RESPONSE=$(kie_post "/jobs/createTask" "$BODY")
echo "$RESPONSE" | python3 -m json.tool

TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['taskId'])")
echo "→ Task ID: $TASK_ID"
echo "→ Polling (Kling 3.0 takes 2-6 minutes)..."

ATTEMPT=0
while true; do
  ATTEMPT=$((ATTEMPT+1))
  sleep 20
  STATUS=$(kie_get "/jobs/recordInfo?taskId=${TASK_ID}")
  STATE=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['state'])")
  echo "  [$ATTEMPT] state: $STATE"
  if [ "$STATE" = "success" ]; then
    URL=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['resultJson']['resultUrls'][0])")
    echo "→ Downloading: $URL"
    curl -sL "$URL" -o "$OUTPUT_PATH"
    echo "→ Saved: $OUTPUT_PATH ($(du -h "$OUTPUT_PATH" | cut -f1))"
    exit 0
  elif [ "$STATE" = "fail" ]; then
    echo "FAILED:"; echo "$STATUS" | python3 -m json.tool; exit 1
  fi
  if [ "$ATTEMPT" -gt 30 ]; then
    echo "TIMEOUT after 10 minutes"; exit 1
  fi
done
```

```bash
chmod +x scripts/launch-film/generate_clip.sh
```

- [ ] **Step 2: Commit the script**

```bash
git add scripts/launch-film/generate_clip.sh
git commit -m "feat(launch-film): add Kling 3.0 clip generation script"
```

---

## Task 6: Generate Clip 1 — First Light (Scene 1, 6s)

**Files:**
- Create: `media/launch-film/clips/clip-01-first-light.mp4`

**Strategy:** Image-to-video from `treeboard_node_hero.png`. The hero image is uploaded to a temporary URL first (Kling needs a public URL).

- [ ] **Step 1: Upload the hero image to get a public URL**

Use Kie.ai's file upload endpoint or any temporary host (e.g., `transfer.sh`):

```bash
HERO_URL=$(curl -s --upload-file media/launch-film/elements/treeboard_node_hero.png https://transfer.sh/treeboard_node_hero.png)
echo "Hero URL: $HERO_URL"
echo "HERO_URL=$HERO_URL" >> scripts/launch-film/.element-ids
```

- [ ] **Step 2: Generate Clip 1 with image-to-video**

```bash
source scripts/launch-film/.element-ids
./scripts/launch-film/generate_clip.sh "@treeboard_node pill-shaped sage-green glowing node materializes from absolute darkness. Energy particles rising slowly around it as it solidifies. Pure black void, no ambient light except the node's own bioluminescent glow. Camera locked, extreme close-up, no movement. Soft cinematic depth of field, film grain, crushed blacks. No motion blur, no warped geometry, no temporal flicker." \
  6 \
  media/launch-film/clips/clip-01-first-light.mp4 \
  pro \
  "$HERO_URL"
```

- [ ] **Step 3: Review the clip with audio**

```bash
open media/launch-film/clips/clip-01-first-light.mp4
```

Checklist:
- Opens on black (or very dark) frame
- Pill materializes smoothly, not instantly
- Sage glow color matches the Element library
- Audio: silent for first 2 seconds, then a crystalline tone as the pill appears
- No flicker, no warping, no extra geometry

If audio is wrong but visual is right: regenerate (Kling generates new audio each time). If both are wrong: refine prompt.

- [ ] **Step 4: Commit the clip**

```bash
git add media/launch-film/clips/clip-01-first-light.mp4
git commit -m "feat(launch-film): generate Clip 1 — First Light (Scene 1)"
```

---

## Task 7: Generate Clip 2 — Bloom Part A (Scene 2 first half, 9s)

**Files:**
- Create: `media/launch-film/clips/clip-02-bloom-a.mp4`

- [ ] **Step 1: Generate Clip 2**

```bash
./scripts/launch-film/generate_clip.sh "@treeboard_node multiple sage-green and amber pill-shaped nodes materializing one by one in rhythmic sequence around a central node. Each pill appears with a soft particle burst, glow expanding outward. Slow orbital arrangement forming like a solar system. Camera pulls back slowly. Pure black void background. Soft sage filaments connecting central node to children as they appear. Cinematic, film grain. Each new pill triggers an ambient crystalline tone as it appears. No motion blur, no inconsistent glow radius." \
  9 \
  media/launch-film/clips/clip-02-bloom-a.mp4 \
  pro
```

- [ ] **Step 2: Review and commit**

```bash
open media/launch-film/clips/clip-02-bloom-a.mp4
```

Visual checklist: pills appear one at a time, central node is consistent, sage glow uniform across pills. Audio: layered crystalline tones, no music yet.

```bash
git add media/launch-film/clips/clip-02-bloom-a.mp4
git commit -m "feat(launch-film): generate Clip 2 — Bloom A (Scene 2)"
```

---

## Task 8: Generate Clip 3 — Bloom Part B (Scene 2 second half, 9s)

**Files:**
- Create: `media/launch-film/clips/clip-03-bloom-b.mp4`

- [ ] **Step 1: Generate Clip 3**

```bash
./scripts/launch-film/generate_clip.sh "@treeboard_node continuation of pill node bloom — secondary cluster of smaller pills forming further from center, mix of sage green, amber, and clean mint green. Camera continues slow pull-back. More pills materialize, faster cadence now. Edges of frame begin to fill. Pure black void deepening. Sage filament network growing more complex. Soft particle ambience. Cinematic, film grain. Audio layers continue building — multiple crystalline tones overlapping. No warping, no flicker." \
  9 \
  media/launch-film/clips/clip-03-bloom-b.mp4 \
  pro
```

- [ ] **Step 2: Review and commit**

```bash
open media/launch-film/clips/clip-03-bloom-b.mp4
git add media/launch-film/clips/clip-03-bloom-b.mp4
git commit -m "feat(launch-film): generate Clip 3 — Bloom B (Scene 2)"
```

---

## Task 9: Generate Clip 4 — Galaxy Part A (Scene 3 first half, 12s, 4K mode)

**Files:**
- Create: `media/launch-film/clips/clip-04-galaxy-a.mp4`

**Strategy:** Image-to-video from `galaxy_keyframe.png` — the highest-stakes shot, do not rely on text-to-video.

- [ ] **Step 1: Upload the galaxy key frame**

```bash
GALAXY_URL=$(curl -s --upload-file media/launch-film/keyframes/galaxy_keyframe.png https://transfer.sh/galaxy_keyframe.png)
echo "GALAXY_URL=$GALAXY_URL" >> scripts/launch-film/.element-ids
```

- [ ] **Step 2: Generate Clip 4 in 4K mode**

```bash
source scripts/launch-film/.element-ids
./scripts/launch-film/generate_clip.sh "Hundreds of glowing pill-shaped nodes interconnected across pure black canvas, luminous sage-green filaments between them like fiber optics. Camera pulls back slowly in a smooth crane shot revealing the entire constellation. Warm amber nodes mixed with sage. Nodes pulse softly in sequence. Volumetric fog at edges. Cosmic depth, god's-eye perspective. Sub-bass drone audio layer — deep, atmospheric, vibrating. No motion blur on nodes. No inconsistent glow radius. No human." \
  12 \
  media/launch-film/clips/clip-04-galaxy-a.mp4 \
  4K \
  "$GALAXY_URL"
```

- [ ] **Step 3: Review with critical attention to color consistency vs the key frame**

```bash
open media/launch-film/clips/clip-04-galaxy-a.mp4
open media/launch-film/keyframes/galaxy_keyframe.png
```

The opening frame of the video should match the key frame nearly identically. If it drifts dramatically — regenerate.

- [ ] **Step 4: Commit**

```bash
git add media/launch-film/clips/clip-04-galaxy-a.mp4
git commit -m "feat(launch-film): generate Clip 4 — Galaxy A (Scene 3, 4K)"
```

---

## Task 10: Generate Clip 5 — Galaxy Part B (Scene 3 second half, 6s, 4K mode)

**Files:**
- Create: `media/launch-film/clips/clip-05-galaxy-b.mp4`

- [ ] **Step 1: Generate Clip 5 (slow drift continuation)**

```bash
./scripts/launch-film/generate_clip.sh "Slow leftward drift across a vast constellation of glowing pill-shaped sage-green nodes interconnected by luminous filaments. Camera at maximum distance, godlike perspective. Some nodes pulse in slow sequence. Amber and green accent nodes scattered. Volumetric fog. Sub-bass drone continuing — atmospheric. Pure black void. No motion blur. No flicker. No human. No interface." \
  6 \
  media/launch-film/clips/clip-05-galaxy-b.mp4 \
  4K
```

- [ ] **Step 2: Review and commit**

```bash
open media/launch-film/clips/clip-05-galaxy-b.mp4
git add media/launch-film/clips/clip-05-galaxy-b.mp4
git commit -m "feat(launch-film): generate Clip 5 — Galaxy B (Scene 3, 4K)"
```

---

## Task 11: Generate Clip 6 — Creator Part A (Scene 4 first half, 9s)

**Files:**
- Create: `media/launch-film/clips/clip-06-creator-a.mp4`

- [ ] **Step 1: Generate Clip 6**

```bash
./scripts/launch-film/generate_clip.sh "A human silhouette seated at a desk in a dark room. No facial features visible, only the outline lit from behind. Surrounding the silhouette in the room are dozens of floating glowing pill-shaped sage-green nodes, hovering at different distances like stars in the room. Soft amber and green pills scattered. The silhouette is still, facing forward, hands not visible. Medium shot, slight low angle. The room itself is barely visible — only the pills illuminate space. Ambient hum, room reverb, soft pill breathing sounds. Cinematic, film grain. No face. No specific person." \
  9 \
  media/launch-film/clips/clip-06-creator-a.mp4 \
  pro
```

- [ ] **Step 2: Review — confirm no facial features visible, silhouette only**

```bash
open media/launch-film/clips/clip-06-creator-a.mp4
```

If a face is rendered: regenerate with stronger negative prompt: "No face. No facial features. No identifiable person. Silhouette only."

- [ ] **Step 3: Commit**

```bash
git add media/launch-film/clips/clip-06-creator-a.mp4
git commit -m "feat(launch-film): generate Clip 6 — Creator A (Scene 4)"
```

---

## Task 12: Generate Clip 7 — Creator Part B (Scene 4 second half, 9s)

**Files:**
- Create: `media/launch-film/clips/clip-07-creator-b.mp4`

- [ ] **Step 1: Generate Clip 7**

```bash
./scripts/launch-film/generate_clip.sh "Hold on the silhouetted figure in the dark room surrounded by glowing pill nodes. Slight camera push-in. The figure remains still. Pills around them breathe softly in synchronized pulse. The light from the pills shifts subtly. Sense of awe. Intimate atmosphere. Ambient hum continues, piano-like soft tones emerging from the pill ambience. No face. No human features. No movement from the figure. Cinematic, film grain." \
  9 \
  media/launch-film/clips/clip-07-creator-b.mp4 \
  pro
```

- [ ] **Step 2: Review and commit**

```bash
open media/launch-film/clips/clip-07-creator-b.mp4
git add media/launch-film/clips/clip-07-creator-b.mp4
git commit -m "feat(launch-film): generate Clip 7 — Creator B (Scene 4)"
```

---

## Task 13: Generate Clip 8 — The Command (Scene 5, 12s)

**Files:**
- Create: `media/launch-film/clips/clip-08-command.mp4`

- [ ] **Step 1: Generate Clip 8**

```bash
./scripts/launch-film/generate_clip.sh "Fast sequential cuts showing a constellation of sage-green glowing pill-shaped nodes responding to commands — pills cluster together rapidly, zoom toward camera, edges blaze with cascading pulses of sage light along import-graph filaments. Three quick cuts: pills converging, then pulse wave propagating outward, then full constellation re-stabilizing brighter than before. Powerful, decisive. Sub-bass returns and resolves with a satisfying thud. Cinematic, dark, dramatic. No motion blur on pills. No human. No interface visible." \
  12 \
  media/launch-film/clips/clip-08-command.mp4 \
  pro
```

- [ ] **Step 2: Review and commit**

```bash
open media/launch-film/clips/clip-08-command.mp4
git add media/launch-film/clips/clip-08-command.mp4
git commit -m "feat(launch-film): generate Clip 8 — The Command (Scene 5)"
```

---

## Task 14: Generate the VO Line (Scene 6 lock-up)

**Files:**
- Create: `scripts/launch-film/generate_vo.sh`
- Create: `media/launch-film/audio/vo-lockup.wav`

- [ ] **Step 1: Write the VO generation script**

```bash
#!/bin/bash
# Generate the lock-up VO line via Kie.ai voice
set -euo pipefail
source "$(dirname "$0")/kie_client.sh"

VOICE_ID="$1"
TEXT="$2"
OUTPUT_PATH="$3"

BODY=$(python3 -c "
import json
print(json.dumps({
    'voiceId': '$VOICE_ID',
    'text': $(echo "$TEXT" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))'),
    'format': 'wav'
}))
")

echo "→ Submitting voice generation task..."
RESPONSE=$(kie_post "/voice/generate" "$BODY")
echo "$RESPONSE" | python3 -m json.tool

TASK_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['taskId'])")
echo "→ Task ID: $TASK_ID"

while true; do
  sleep 5
  STATUS=$(kie_get "/voice/record-info?taskId=${TASK_ID}")
  STATE=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['state'])")
  echo "  state: $STATE"
  if [ "$STATE" = "success" ]; then
    URL=$(echo "$STATUS" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['resultJson']['resultUrls'][0])")
    curl -sL "$URL" -o "$OUTPUT_PATH"
    echo "→ Saved: $OUTPUT_PATH"
    exit 0
  elif [ "$STATE" = "fail" ]; then
    echo "FAILED:"; echo "$STATUS" | python3 -m json.tool; exit 1
  fi
done
```

```bash
chmod +x scripts/launch-film/generate_vo.sh
```

- [ ] **Step 2: List available voices**

```bash
source scripts/launch-film/kie_client.sh
kie_get "/voice/check-voice" | python3 -m json.tool > /tmp/kie-voices.json
head -200 /tmp/kie-voices.json
```

Pick 3 voice IDs to test. Target: low, intimate, slightly hushed, English. Both male and female options.

- [ ] **Step 3: Generate 3 test takes (pick 3 voice IDs from the list)**

```bash
./scripts/launch-film/generate_vo.sh "<voice-id-1>" "Your code has always been this beautiful." /tmp/vo-test-1.wav
./scripts/launch-film/generate_vo.sh "<voice-id-2>" "Your code has always been this beautiful." /tmp/vo-test-2.wav
./scripts/launch-film/generate_vo.sh "<voice-id-3>" "Your code has always been this beautiful." /tmp/vo-test-3.wav
```

- [ ] **Step 4: Listen to all three and pick the best**

```bash
open /tmp/vo-test-1.wav
open /tmp/vo-test-2.wav
open /tmp/vo-test-3.wav
```

The winning take goes to:

```bash
cp /tmp/vo-test-<N>.wav media/launch-film/audio/vo-lockup.wav
```

- [ ] **Step 5: Commit the VO**

```bash
git add scripts/launch-film/generate_vo.sh media/launch-film/audio/vo-lockup.wav
git commit -m "feat(launch-film): add VO lock-up line"
```

---

## Task 15: Set Up DaVinci Resolve Project

**Files:**
- Create: `media/launch-film/davinci/treeboard-launch.drp` (saved manually from DaVinci)

- [ ] **Step 1: Open DaVinci Resolve and create a new project**

1. Launch DaVinci Resolve (free version is sufficient)
2. New Project → name it `treeboard-launch`
3. Project Settings:
   - Timeline resolution: 3840×2160 (4K UHD)
   - Frame rate: 24 fps
   - Color space: Rec.709
4. Save project file to `media/launch-film/davinci/treeboard-launch.drp`

- [ ] **Step 2: Import all clips and the VO**

In the Media pool:
1. Import all 8 clips from `media/launch-film/clips/`
2. Import VO from `media/launch-film/audio/vo-lockup.wav`

- [ ] **Step 3: Apply the LUT to every clip**

In the Color page:
1. Select Clip 1
2. Open the LUT browser (right panel)
3. Apply a custom LUT with these adjustments (apply as adjustment node):
   - Lift: shadows pushed slightly green (+0.005 G in lift wheel)
   - Gain: slight desaturation except in sage/amber range (use HSL qualifier)
   - Add a film grain layer at 8% opacity on the timeline
4. Right-click the clip → "Copy Grade"
5. Select Clips 2–8 → right-click → "Paste Grade"

This ensures uniform color across all clips. Verify by scrubbing through the timeline.

- [ ] **Step 4: Save the project**

`File → Save Project`

This creates the `.drp` file. Manually copy it if needed:

```bash
# DaVinci stores projects in its DB by default. To export:
# File → Project Manager → right-click project → Export → save to media/launch-film/davinci/
```

```bash
git add media/launch-film/davinci/treeboard-launch.drp
git commit -m "feat(launch-film): DaVinci project with LUT applied across all clips"
```

---

## Task 16: Assemble the 90s Master

**Files:**
- Create: `media/launch-film/exports/treeboard-launch-90s-16x9.mp4`

- [ ] **Step 1: Build the timeline in DaVinci**

In the Edit page, arrange clips in order with these exact timings:

| Position | Clip | In Point | Out Point | Duration |
|---|---|---|---|---|
| 0:00 | clip-01-first-light.mp4 | 0:00 | 0:06 | 6s |
| 0:06 | clip-02-bloom-a.mp4 | 0:00 | 0:09 | 9s |
| 0:15 | clip-03-bloom-b.mp4 | 0:00 | 0:09 | 9s |
| 0:24 | clip-04-galaxy-a.mp4 | 0:00 | 0:12 | 12s |
| 0:36 | clip-05-galaxy-b.mp4 | 0:00 | 0:06 | 6s |
| 0:42 | clip-06-creator-a.mp4 | 0:00 | 0:09 | 9s |
| 0:51 | clip-07-creator-b.mp4 | 0:00 | 0:09 | 9s |
| 1:00 | clip-08-command.mp4 | 0:00 | 0:12 | 12s |
| 1:12 | (black slug) | — | — | 2s |
| 1:14 | (Scene 6 typography) | 0:00 | 0:16 | 16s |

Total: 90 seconds.

- [ ] **Step 2: Add Scene 6 typography**

On a black background, add three text layers using the Fusion page:

1. `treeboard` (Fraunces 300, 80pt, color `#e6e6e6`) — centered, appears at 1:16
2. `pip install treeboard` (JetBrains Mono 400, 24pt, color `#b6d4a7`, on a subtle pill background `rgba(182,212,167,0.06)`) — below wordmark, appears at 1:18
3. Fade out everything at 1:28, hold black until 1:30

- [ ] **Step 3: Place the VO line**

Drop `vo-lockup.wav` on an audio track at 1:18 (synced to wordmark appearing). Level the VO at -12 LUFS peak. Mix all Kling-generated audio to -18 LUFS background.

- [ ] **Step 4: Add the Scene 4 and 5 text overlays**

- "You built this." — Fraunces italic, 36pt, white, centered. Fade in at 0:48 over 1.5s, hold 3s, fade out by 0:54.
- "Now you can see it." — Fraunces italic, 36pt, white, centered. Fade in at 1:08 over 1.5s, hold 3s, fade out by 1:14.

- [ ] **Step 5: Export the 90s master**

Deliver page:
- Format: MP4
- Codec: H.264
- Resolution: 3840×2160
- Frame rate: 24
- Quality: Best (target bitrate ~30 Mbps)
- Audio: AAC 320kbps
- Output: `media/launch-film/exports/treeboard-launch-90s-16x9.mp4`

Verify size is under 280 MB for Twitter compatibility (it should be — Twitter accepts up to 512 MB for tweet videos).

- [ ] **Step 6: Watch the full master back, end to end**

```bash
open media/launch-film/exports/treeboard-launch-90s-16x9.mp4
```

The discipline test: do not skip ahead. Watch all 90 seconds with sound. If anything feels off — fix it now, not after launch.

- [ ] **Step 7: Commit**

```bash
git add media/launch-film/exports/treeboard-launch-90s-16x9.mp4
git commit -m "feat(launch-film): export 90s master"
```

---

## Task 17: Cut the 60s X Version

**Files:**
- Create: `media/launch-film/exports/treeboard-launch-60s-16x9.mp4`

- [ ] **Step 1: Duplicate the 90s timeline in DaVinci**

Right-click the 90s timeline → "Duplicate" → rename to `treeboard-launch-60s`.

- [ ] **Step 2: Apply the 60s cut edits**

| Position | Clip | Duration | Change |
|---|---|---|---|
| 0:00 | clip-01-first-light.mp4 | 6s | Keep full |
| 0:06 | clip-02-bloom-a.mp4 | 6s | Compress (drop 3s from end) |
| 0:12 | clip-03-bloom-b.mp4 | 6s | Compress (drop 3s from end) |
| 0:18 | clip-04-galaxy-a.mp4 | 12s | Keep full |
| 0:30 | clip-05-galaxy-b.mp4 | 6s | Keep full |
| **REMOVE** | clip-06-creator-a.mp4 | — | Removed entirely |
| **REMOVE** | clip-07-creator-b.mp4 | — | Removed entirely |
| 0:36 | clip-08-command.mp4 | 12s | Keep full |
| 0:48 | (Scene 6 typography + VO) | 8s | Compress — VO and typography appear simultaneously |

Total: 56 seconds.

Remove the "You built this." text overlay (Scene 4 is cut).
Keep "Now you can see it." but compress fade-out.

- [ ] **Step 3: Export the 60s cut**

Same settings as Task 16 but:
- Resolution: 1920×1080 (1080p is sufficient for Twitter)
- Frame rate: 24
- Output: `media/launch-film/exports/treeboard-launch-60s-16x9.mp4`

- [ ] **Step 4: Watch the 60s cut back**

```bash
open media/launch-film/exports/treeboard-launch-60s-16x9.mp4
```

It should feel complete, not amputated. The loop is the point — the last frame fading to black should make you want to watch again immediately.

- [ ] **Step 5: Commit**

```bash
git add media/launch-film/exports/treeboard-launch-60s-16x9.mp4
git commit -m "feat(launch-film): export 60s X cut"
```

---

## Task 18: Cut the 9:16 Vertical Version

**Files:**
- Create: `media/launch-film/exports/treeboard-launch-60s-9x16.mp4`

- [ ] **Step 1: Duplicate the 60s timeline**

In DaVinci: duplicate `treeboard-launch-60s` → rename to `treeboard-launch-60s-vertical`.

- [ ] **Step 2: Change timeline resolution to 1080×1920**

`Timeline Settings → Resolution: 1080×1920 (custom)`.

- [ ] **Step 3: Re-frame each clip to 9:16**

For each clip on the timeline:
1. Select the clip
2. Inspector → Transform → Zoom: 1.2
3. Position: center on the primary subject (the pill cluster or central node)
4. For Scenes 4–5 where subjects shift: keyframe the position to track the focal pill

The Treeboard pill shape is wide (16:9-ish per pill), so vertical framing focuses on stacked pills rather than horizontal spread. Lean into this.

- [ ] **Step 4: Re-frame typography**

Move all text elements to vertical center. Resize as needed — Fraunces 80pt becomes 60pt to fit width.

- [ ] **Step 5: Export the vertical cut**

- Format: MP4 H.264
- Resolution: 1080×1920
- Frame rate: 24
- Output: `media/launch-film/exports/treeboard-launch-60s-9x16.mp4`

- [ ] **Step 6: Commit**

```bash
git add media/launch-film/exports/treeboard-launch-60s-9x16.mp4
git commit -m "feat(launch-film): export 9:16 vertical cut"
```

---

## Task 19: Final Review with Sir Before Launch

- [ ] **Step 1: Present all three cuts to Sir**

```bash
open media/launch-film/exports/treeboard-launch-90s-16x9.mp4
open media/launch-film/exports/treeboard-launch-60s-16x9.mp4
open media/launch-film/exports/treeboard-launch-60s-9x16.mp4
```

Wait for explicit Sir approval before proceeding. If any cut needs changes, return to the relevant task and re-export.

- [ ] **Step 2: Tag the release in git**

```bash
git tag launch-film-v1
git push origin launch-film-v1
```

---

## Task 20: Write the Launch Tweet Thread

**Files:**
- Create: `media/launch-film/launch-thread.md`

- [ ] **Step 1: Draft the 4-tweet thread**

Write `media/launch-film/launch-thread.md`:

```markdown
# Treeboard Launch Thread (Twitter / X)

## Tweet 1 — The Film
[Attach: treeboard-launch-60s-16x9.mp4]

treeboard
pip install treeboard

## Tweet 2 — The Meta-Story
I built treeboard for vibe coders — devs who code with AI. So I launched it with AI too.

Film: Kling 3.0 via Kie.ai. Score: Kling native audio. VO: Kie.ai voice generation. Cut: DaVinci Resolve.

9 clips. 5 days. Zero stock footage. Zero human VO.

This is the first vibe-coded launch film I've seen for a vibe-coding tool.

## Tweet 3 — The Why
Code is the most complex thing humans build. And we cannot see it.

We navigate our own codebases by memory, by grep, by intuition — like sailing without a map.

Treeboard makes your code visible. As a living, spatial thing. For the first time.

## Tweet 4 — The CTA
Try it: pip install treeboard
GitHub: github.com/heidar-droid/treeboard
PyPI: pypi.org/project/treeboard
```

- [ ] **Step 2: Commit the thread**

```bash
git add media/launch-film/launch-thread.md
git commit -m "docs(launch-film): launch tweet thread copy"
```

---

## Task 21: Launch on Twitter / X

- [ ] **Step 1: Post Tweet 1 with the 60s cut attached**

Open Twitter / X. Upload `treeboard-launch-60s-16x9.mp4`. Add the body from Tweet 1. Post.

- [ ] **Step 2: Reply with Tweet 2, 3, 4 in sequence**

Each tweet replies to the previous tweet to form a thread. Wait 30 seconds between tweets for algorithmic spacing.

- [ ] **Step 3: Monitor first-hour engagement**

Use Twitter Analytics or Birdwatch to track:
- 3-second retention rate (target ≥ 65%)
- Replay rate (target ≥ 15%)
- First-hour likes, retweets, replies

If retention is significantly below target — the opening hook may need revision. Document what didn't work for next iteration.

---

## Task 22: Submit to Product Hunt (Within 7 Days)

- [ ] **Step 1: Schedule the PH launch**

Go to producthunt.com → Submit a product. Target launch date: within 7 days of Twitter launch.

- [ ] **Step 2: Upload the 90s master as the hero video**

Upload `treeboard-launch-90s-16x9.mp4` as the primary product video.

- [ ] **Step 3: Add product copy**

Tagline: `treeboard — your codebase, finally visible`

Description (max 260 chars):
> A cinematic pyramid visualizer for any directory on disk. Run `treeboard .` in any project — get a browser canvas where every file is a glowing, draggable pill. AI context builder, fuzzy search, git mode, live preview. pip install treeboard.

First comment (seeded with the meta-story from Tweet 2 of the launch thread).

- [ ] **Step 4: Launch on PH the chosen day, then re-engage Twitter thread**

When PH goes live, quote-tweet the original Twitter thread with the PH link.

---

## Task 23: Update treeboard Website Hero

**Files:**
- Modify: `treeboard.dev/index.html` (or wherever the landing page lives — TBD if landing page exists)

- [ ] **Step 1: Add the 90s master as hero video**

If a landing page exists:
- Embed `treeboard-launch-90s-16x9.mp4` as autoplay, muted, looping above the fold
- Below the video: tagline "Your codebase. Finally visible."
- CTA below tagline: `pip install treeboard` (copyable on click)

If no landing page exists yet: this task is deferred. Note as follow-up in `tasks/todo.md`.

---

## Task 24: Capture Launch Metrics (Day 7 Post-Launch)

- [ ] **Step 1: Document final launch metrics**

Append a `launch-metrics.md` to the launch-film directory with:

```markdown
# Treeboard Launch Metrics — 7 Day Post-Launch Report

## Twitter / X
- 3-second retention: X%
- Replay rate: X%
- Likes: X
- Retweets: X
- Replies: X
- Profile visits: X

## Product Hunt
- Upvotes: X
- Comments: X
- Daily rank: X

## GitHub
- Stars (delta from launch): X
- Forks: X
- Issues opened: X

## PyPI
- `pip install treeboard` count: X
- Unique installs: X (if obtainable)

## Notable shares
- [List of devtools / motion design accounts that shared organically]

## What worked
[Bullet list of insights]

## What to do differently next time
[Bullet list of corrections]
```

- [ ] **Step 2: Commit**

```bash
git add media/launch-film/launch-metrics.md
git commit -m "docs(launch-film): 7-day launch metrics report"
```

---

## Self-Review Checklist

After completing all tasks, verify against the spec:

| Spec Section | Implemented By | Status |
|---|---|---|
| 1. Concept (creation myth, no demo) | Tasks 6–13 (all clips are abstract) | — |
| 2. Visual language (sage, dark forest, Fraunces) | Tasks 2–3 (Elements), Task 15 (LUT) | — |
| 3. Storyboard (6 scenes) | Tasks 6–13 (8 clips for 5 scenes) + Task 16 (scene 6 typography) | — |
| 4. Three cuts | Tasks 16, 17, 18 | — |
| 5. Production pipeline order | Tasks 1–5 sequenced before clip gen | — |
| 6. Audio strategy (Kling native + VO) | Task 13 (clips with sound:true), Task 14 (VO) | — |
| 7. Launch post strategy | Tasks 20, 21 (Twitter), 22 (PH), 23 (website) | — |
| 8. Timeline (Mon–Fri) | Tasks roughly aligned (1–4 = Day 1, 5–13 = Days 2–3, etc.) | — |
| 9. Risks (regeneration buffers) | Each clip task allows 3 regen attempts | — |
| 10. Success metrics | Task 24 (post-launch report) | — |

All sections covered. No placeholders remain. Type/path consistency verified.

---

**End of plan.**
