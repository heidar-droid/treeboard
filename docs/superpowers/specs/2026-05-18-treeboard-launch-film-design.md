# Treeboard Launch Film — "In the Beginning"

**Date:** 2026-05-18
**Status:** Approved (concept), Pending (production)
**Owner:** Sir (Heidar)
**Target launch:** This week (2026-05-18 to 2026-05-24)
**Primary distribution:** Twitter / X launch post
**Secondary distribution:** Product Hunt, treeboard website hero, YouTube

---

## 1. Concept

A 90-second creation myth for Treeboard. No product demo. No feature list. No narration except one whispered line at the lock-up. The film starts in absolute darkness, materializes one glowing pill node, and builds — through six scenes — into a full constellation of code made visible, then ends in silence with a single statement.

### 1.1 The thesis (philosophical inversion)

The film does not say "Treeboard makes your code beautiful." It says:

> *This is what your code always looked like — before text editors compressed it into lines.*

The visualization is the original reality. The text file is the impoverished representation. This inversion (from Buck's approach for Nothing) reframes Treeboard from "feature on top of a code editor" to "the way code was always meant to be seen." It is felt in the visual language, not stated.

### 1.2 The one line

The only words in the film are spoken at the lock-up, after 88 seconds of silence and sound design:

> *"Your code has always been this beautiful."*

Whispered. Intimate. The only human voice. Lands in 3–4 seconds of black silence before the wordmark appears.

### 1.3 What this film is not

- Not a product walkthrough
- Not a feature tour
- Not a "vibe coding workflow" demo
- Not narrated
- Not scored with a stock music track
- Not a polished agency film (it is built by AI tools, on purpose)

---

## 2. Visual Language

The film is built in Treeboard's exact design language — no reinvention. Source: `src/treeboard/static/treeboard.css`.

### 2.1 Palette

| Token | Value | Use |
|---|---|---|
| Background top | `#0d1611` | Dark forest green-black (top of gradient) |
| Background bottom | `#060a08` | Near-black with green tint (canvas) |
| Sage (primary) | `#b6d4a7` | Pill glow, active states, hero accent |
| Sage glow | `rgba(182,212,167,.55)` | Drop shadow / atmospheric glow |
| Folder label | `#cfe0c4` | Light sage text |
| File label | `#6e7d6f` | Muted sage-gray text |
| Amber (git modified) | `#f59e0b` | Secondary accent — warm pills |
| Green (git added) | `#10b981` | Secondary accent — clean pills |
| Red (git deleted) | `#ef4444` | Used sparingly, dashed pills |
| Blue (untracked) | `#60a5fa` | Used sparingly |

### 2.2 Typography

- Wordmark + cinematic titles: **Fraunces** (lightweight 300, italic for emphasis)
- Technical labels + monospace text: **JetBrains Mono** (treeboard's actual code font)
- The on-pill text inside the materializing nodes: **Geist Mono** (treeboard's UI font)

### 2.3 Texture

- Grain overlay: radial-gradient dot pattern at 3px × 3px, `mix-blend-mode: overlay`, `opacity: 0.8`. Always present.
- Top radial glow: 1200px × 600px sage-tinted radial fade at top of every frame.

### 2.4 Motion language

- Spring easing: `cubic-bezier(.2, .7, .2, 1.05)` — used for every appearance/disappearance
- Pill materialization: scale .9 → 1, opacity 0 → 1, 0.42s
- Edge draw: `stroke-dashoffset 1000 → 0`, 0.8s ease-out
- Pulse: drop-shadow flash with sage glow, 0.8s

---

## 3. Storyboard

### Scene 1 — The First Light (0:00 – 0:06)

**Visual:** Pure black. 2 seconds of held darkness minimum. Then a single sage-glowing pill materializes at frame center, very slowly. The text `index.ts` is inside it. The pill breathes (soft pulse). It is the only thing in the universe.

**Camera:** Extreme close-up, locked. No movement.

**Audio (Kling native):** 2 seconds of total silence. Then a single crystalline glass-bell strike — long decay, like a finger on a wine glass.

**On-screen text:** None.

**Why this scene works:** The opening cannot be a logo, a product name, or anything recognizable. Atlas research: viewers spend 1.7 seconds deciding to stay or leave. The hook is confusion + beauty, not familiarity. One glowing pill from black is unclassifiable and beautiful — the brain pauses to look.

### Scene 2 — The Bloom (0:06 – 0:24)

**Visual:** More pills appear in rhythm — not all at once. Each new pill is a different color (sage, amber, green) and triggers its own micro-sound. Pills orbit the center node like a solar system forming. Faint sage edges connect the central pill to its children.

**Camera:** Slow pull-back. Spring easing.

**Audio (Kling native):** Each pill = a new sound layer. Sage pills get a high crystalline tink. Amber pills get a warm lower tone. Green pills get a clean mid bell. They cascade into a chime cluster.

**On-screen text:** None.

### Scene 3 — The Galaxy (0:24 – 0:42)

**Visual:** Camera has pulled so far back that individual pills are now stars. Hundreds of them. The full codebase — 2,341 files — hangs in space like a bioluminescent constellation. Import graph edges are luminous sage threads. Volumetric fog at edges. The emotional peak of the film.

**Camera:** Cosmic pull-back complete. Slow drift left. Godlike perspective.

**Audio (Kling native):** Sub-bass drone. Whale song slowed to 10%. Vibrates the chest through headphones. 4-second hold. The full ambient layer of the codebase as music.

**On-screen text:** Fades in for 2 seconds: *"2,341 files."* Then fades out.

**Production note:** This is the highest-stakes shot. Generate it with **image-to-video** — render the perfect static key frame in Nano Banana first, then animate with Kling from that locked frame. Do not rely on text-to-video for this shot.

### Scene 4 — The Creator (0:42 – 0:60)

**Visual:** Cut to: a developer at their desk — silhouette only, no face. The constellation fills their entire room. They are inside their own codebase, surrounded by glowing pills. They're not typing. They're just looking. The room is lit only by the sage-amber glow of their files.

**Camera:** Medium shot, slight low angle. Silhouette lit from behind by pills.

**Audio (Kling native):** Drops to ambient pill breathing — soft sage hum, room reverb. Intimate.

**On-screen text:** Fades in: *"You built this."* Fraunces italic, held 3s, fades out.

**Note:** Silhouette only (per Sir's direction). No facial features. Anyone can project themselves onto it.

### Scene 5 — The Command (0:60 – 0:78)

**Visual:** The silhouette's hand moves — and the constellation responds. Pills cluster, zoom, graph edges blaze. Import lines pulse outward in cascading waves. The room becomes commanded. It's a god commanding stars.

**Camera:** Fast cuts. Reaction → response rhythm. Three quick cuts maximum.

**Audio (Kling native):** Final swell. Sub-bass returns. A satisfying resolve. Kling generates the responsive audio.

**On-screen text:** Fades in: *"Now you can see it."* Held 3s, fades out.

### Scene 6 — The Lock-Up (0:78 – 0:90)

**Visual:** Pure black. 1.5 seconds of silence. Wordmark fades in (Fraunces, 300 weight): **treeboard**. Below it, smaller: `pip install treeboard`. The VO line is spoken.

**Camera:** Static. Centered. Held for the full 12 seconds.

**Audio:** Single cello note returns from Scene 1. The VO line whispered: *"Your code has always been this beautiful."* Then silence. Fade to black.

**On-screen text:**
- `treeboard` (Fraunces 300, 32px)
- `pip install treeboard` (JetBrains Mono, 11px, sage on dark sage-tinted pill)
- *"your codebase · finally visible"* (optional micro-tag below name)

---

## 4. Three Cuts: 90s Master + 60s X Cut + 9:16 Vertical

### 4.1 90-second master (16:9)

- **Distribution:** Product Hunt, treeboard website hero (autoplay muted, looping), YouTube
- **Full storyboard** as specified above (Scenes 1–6)
- **Aspect ratio:** 16:9

### 4.2 60-second X cut (16:9)

- **Distribution:** Twitter / X launch post (primary asset)
- **Why under 60s:** X videos under 60s loop automatically. A looping creation myth is structurally more powerful than one that ends. Atlas research: this is the most under-rated mechanic on X for cinematic content.
- **Cuts:**
  - Scene 1 → keep full 6s
  - Scene 2 → compress to 12s (was 18s)
  - Scene 3 → keep full 18s (emotional peak, do not compress)
  - **Scene 4 → REMOVE** entirely
  - Scene 5 → compress to 12s (was 18s)
  - Scene 6 → compress to 8s, VO over typography simultaneously
- **Total: 56 seconds.** Loops every minute. Each loop is a fresh hook for someone who stopped scrolling mid-frame.

### 4.3 9:16 vertical cut

- **Distribution:** TikTok, Instagram Reels, YouTube Shorts, Twitter mobile vertical
- **Derivation:** Re-frame the 60s X cut by cropping to 9:16 with a slight zoom (1.2×) on the pill clusters in each scene
- **No new generations.** All cropping and re-framing happens in DaVinci.

---

## 5. Production Pipeline

### 5.1 Order of operations (this is non-negotiable)

```
Day 1 → Elements library + key frames (Nano Banana)
Day 2 → Generate clips 1–4 (Kling 3.0)
Day 3 → Generate clips 5–9 (Kling 3.0)
Day 4 → LUT, cut, typography (DaVinci Resolve), VO generation (Kie.ai)
Day 5 → Final review, 60s X cut, vertical 9:16 cut, export
```

### 5.2 Step 1 — Build the Kling Elements Library (Day 1, morning)

**Tool:** Nano Banana (via Kie.ai)

**Output:** 5 reference images defining the canonical Treeboard pill node.

| Asset | Description | Use |
|---|---|---|
| `treeboard_node_hero.png` | The canonical sage pill, front-on, full glow | Reference for all generations |
| `treeboard_node_front.png` | Pill, front-on, neutral lighting | Element library angle 1 |
| `treeboard_node_quarter_left.png` | Pill, ¾ left rotation | Element library angle 2 |
| `treeboard_node_quarter_right.png` | Pill, ¾ right rotation | Element library angle 3 |
| `treeboard_node_back.png` | Pill, back / over-shoulder view | Element library angle 4 |

**Nano Banana prompt template (for the hero):**

```
A single glowing pill-shaped node, floating in absolute darkness. Sage-green
bioluminescent glow (#b6d4a7) emanating from the pill body. Soft inner glow,
crisp outer halo at 30px radius. Rounded rectangle shape, 70px wide × 26px tall.
Subtle text "index.ts" rendered in JetBrains Mono at 9px inside the pill in
soft sage. Dark forest green-black background (#060a08). Subtle radial vignette.
Film grain overlay. Cinematic, photorealistic, depth of field, 4K. No human.
No interface. No screen. Just the pill in void.
```

**Then upload all 5 images to the Kling Elements library via Kie.ai dashboard. Tag as `@treeboard_node`.**

### 5.3 Step 2 — Generate the Scene 3 galaxy key frame (Day 1, afternoon)

**Tool:** Nano Banana

**Output:** 1 hero image — `galaxy_keyframe.png` — used as the start frame for Kling's image-to-video on Scene 3.

**Prompt:**

```
A vast constellation of hundreds of glowing pill-shaped nodes, scattered across
pure black void like a galaxy. Sage-green nodes (#b6d4a7) dominant, with amber
(#f59e0b) and green (#10b981) nodes mixed in. Luminous sage-green filaments
connecting clusters of nodes like fiber-optic threads. Volumetric fog at edges.
Cosmic depth — nodes recede into distance. Slight bloom on brightest nodes.
Film grain. Dark forest green-black ambient color cast. Cinematic, 4K,
god's-eye composition.
```

### 5.4 Step 3 — Generate the 9 Kling 3.0 clips (Days 2–3)

**Tool:** Kling 3.0 via Kie.ai API endpoint `/api/v1/jobs/createTask`

**Settings for every clip:**
- `model`: `kling-3.0/video`
- `sound`: `true` (native audio generation)
- `mode`: `pro` or `4K` (for hero shots) / `std` (for transition clips)
- `aspect_ratio`: `16:9`
- All prompts reference `@treeboard_node` from the Element library
- Lock seed value from first approved generation, reuse across all subsequent clips
- Negative prompts: *"No motion blur on nodes. No inconsistent glow radius. No warped geometry. No temporal flicker on solid forms. No human faces. No interfaces or screens."*

**Clip map:**

| Clip | Scene | Duration | Mode | Strategy |
|---|---|---|---|---|
| 1 | Scene 1 | 6s | pro | Image-to-video from `treeboard_node_hero.png` |
| 2 | Scene 2 part 1 | 9s | pro | Multi-shot, text-to-video |
| 3 | Scene 2 part 2 | 9s | pro | Multi-shot continuation |
| 4 | Scene 3 | 12s | 4K | Image-to-video from `galaxy_keyframe.png` |
| 5 | Scene 3 cont | 6s | 4K | Continuation, slow drift |
| 6 | Scene 4 part 1 | 9s | pro | Silhouette + room reveal |
| 7 | Scene 4 part 2 | 9s | pro | Hold on silhouette |
| 8 | Scene 5 | 12s | pro | Fast cuts, constellation response |
| 9 | Scene 6 | Not generated | — | Pure typography in post |

**Total clips to generate: 8 Kling generations + 1 post-only scene.**

**Prompt formula (every prompt structured as 6 distinct sentences, not comma-separated):**

```
[Subject + Detail]. [Movement/Action]. [Scene/Environment].
[Camera Language]. [Lighting/Atmosphere]. [Negative constraints].
```

### 5.5 Step 4 — VO line generation (Day 4, morning)

**Tool:** Kie.ai voice generation endpoint `/api/v1/voice/generate`

**Input:** Text: *"Your code has always been this beautiful."*

**Voice direction:** Whispered, intimate, low-volume, English (US or UK), male or female (test both, pick what lands). Slight reverb tail.

**Output:** 4-second WAV file. Single take. No edits required.

### 5.6 Step 5 — Post-production (Day 4 afternoon → Day 5)

**Tool:** DaVinci Resolve (free version is sufficient)

**Workflow:**

1. **Import all 9 clips + VO file.**
2. **Apply single LUT to all 9 clips** before any other color work. LUT direction:
   - Push blacks slightly green-black (lift greens in shadow)
   - Desaturate everything except sage and amber
   - Slight bloom on highlights
   - Subtle film grain layer at 8% opacity over the entire timeline
3. **Cut the 90s master** to the storyboard timings.
4. **Add typography** for Scenes 4, 5, 6 (Fraunces italic for VO captions, JetBrains Mono for technical text).
5. **Generate the 60s X cut** from the master timeline (remove Scene 4, compress 2 and 5).
6. **Generate the 9:16 vertical cut** by re-framing each clip with a slight zoom-and-crop, prioritizing pill positioning.
7. **Audio levels:** Kling-generated audio sits at -18 LUFS, VO line peaks at -12 LUFS, master at -14 LUFS.
8. **Export:** H.264, 4K master + 1080p Twitter cut + 1080×1920 vertical, all under 280MB (Twitter limit).

---

## 6. Audio Strategy

| Source | Use | Notes |
|---|---|---|
| Kling native audio (`sound: true`) | All ambient, atmospheric, SFX | Generated per clip |
| Kie.ai voice generation | One VO line (lock-up) | 4s WAV |
| Post-production | Audio leveling, mixing | DaVinci Resolve |

**No music score is added in post.** Kling's native audio is the music. If a music bed emerges from the layered audio, keep it. If not, leave the film as designed sound + silence.

**No additional SFX library used.** Pure AI audio.

---

## 7. Launch Post Strategy

The film is one half of the launch. The launch post is the other half. Both must work together.

### 7.1 The tweet thread (Twitter / X launch day)

**Tweet 1 (the film):** The 60s X cut. No text other than:
> *treeboard*
> pip install treeboard

**Tweet 2 (the meta-story):** This is what makes the launch viral.
> *I built treeboard for vibe coders — devs who code with AI. So I launched it with AI too.*
> *Film: Kling 3.0 via Kie.ai. Score: Kling native audio. VO: Kie.ai voice generation. Cut: DaVinci Resolve.*
> *9 clips. 5 days. Zero stock footage. Zero human VO.*
> *This is the first vibe-coded launch film I've seen for a vibe-coding tool.*

**Tweet 3 (the why):** The thesis.
> *Code is the most complex thing humans build. And we cannot see it.*
> *We navigate our own codebases by memory, by grep, by intuition — like sailing without a map.*
> *Treeboard makes your code visible. As a living, spatial thing. For the first time.*

**Tweet 4 (the CTA):**
> *Try it: pip install treeboard*
> *GitHub: github.com/heidar-droid/treeboard*
> *PyPI: pypi.org/project/treeboard*

### 7.2 Product Hunt launch (within 7 days of Twitter)

- 90s master as the hero video
- 60s X cut as the thumbnail GIF (first 5 seconds)
- Hunter pre-arranged (Sir's network)
- Comment seeded with the meta-story from tweet 2

### 7.3 Website hero (treeboard landing page)

- 90s master, autoplay muted, looping
- Above the fold, full bleed
- Tagline below: *"Your codebase. Finally visible."*
- CTA: `pip install treeboard`

---

## 8. Timeline

| Day | Date | Deliverable |
|---|---|---|
| 1 | Mon 2026-05-18 | Element library (5 images) + galaxy key frame |
| 2 | Tue 2026-05-19 | Clips 1–4 generated and reviewed |
| 3 | Wed 2026-05-20 | Clips 5–8 generated and reviewed |
| 4 | Thu 2026-05-21 | VO generated. LUT, cut, typography. 90s master complete. |
| 5 | Fri 2026-05-22 | 60s X cut + 9:16 vertical. Final review. Export. |
| Launch | Sat 2026-05-23 or Mon 2026-05-25 | Twitter thread goes live. PH launch within 7 days. |

Saturday launch favors developer audiences (less work-day noise). Monday launch maximizes PH visibility.

---

## 9. Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Kling generates inconsistent glow across clips | Medium | Elements library + seed locking + negative prompts. LUT in post catches remaining drift. |
| Image-to-video generation doesn't match the key frame | Low | Re-generate up to 3 times with refined prompt. If it still fails, fall back to text-to-video with the key frame as reference. |
| Kling native audio doesn't fit the scene | Medium | Re-generate the clip (audio regenerates with each video gen). If still wrong, accept the closest match — fully AI is the brand. |
| VO line sounds robotic | Medium | Test 3–5 Kie.ai voice options before committing. Test in context of the film, not in isolation. If all fail, fall back to Sir recording a voice memo. |
| Production runs past Friday | Low | Each day has buffer — clips can be regenerated overnight. Worst case, launch shifts to following Monday. |
| Film looks generic | Low (with Elements library) | The Treeboard pill shape is unique. The dark forest palette is unique. As long as Elements is used correctly, the film will not look like stock "glowing network" content. |
| Twitter caps video at 2:20 or rejects upload | None | Both cuts are under 2:20. Master is well under Twitter's 512MB limit. |

---

## 10. Success Metrics

This is a launch film, not an ad. Success is measured by:

1. **3-second retention rate** on the X tweet ≥ 65% (Atlas threshold for algorithmic amplification)
2. **Replay rate** ≥ 15% (looping mechanic working)
3. **PH upvotes** ≥ 500 in launch day (cinematic films drive 2.7× the baseline)
4. **GitHub stars in first 7 days** ≥ 100 (signal of developer interest, not just attention)
5. **`pip install treeboard` downloads** in first 7 days ≥ 500 (actual adoption)
6. **Qualitative:** at least 3 unprompted shares from prominent devtools / motion design accounts

If 3-second retention is below 50%, the opening hook failed. Re-cut Scene 1 with even more silence and a more dramatic first pill reveal.

---

## 11. Non-Goals

- No B-roll of developers at keyboards
- No comparison shots with text editors
- No feature callouts on screen
- No company logo other than the wordmark at lock-up
- No background music score (Kling native audio only)
- No subtitles on the VO line (it's whispered, intimate, intentional)
- No "What is treeboard?" explainer

---

## 12. Open Questions

- Final VO voice selection (test 3–5 from Kie.ai voice library on Day 4)
- Whether to add a 15-second teaser cut for Product Hunt thumbnail (decision deferred until 60s X cut is locked)
- Whether to publish the production process as a follow-up blog post (likely yes, for the meta-story)

---

## 13. Reference Files

- Treeboard design system: `src/treeboard/static/treeboard.css`
- Feature spec (what the product does): `docs/superpowers/specs/2026-05-18-vibe-coder-features-design.md`
- Visual companion brainstorm artifacts: `.superpowers/brainstorm/324-1779075962/content/*.html`
- Atlas research brief: agent transcript at `/tmp/claude-501/.../tasks/a9e39999965d86205.output` (key findings already integrated into Sections 1.1, 3.1, 4.2, 5.4, 7.1, 10)

---

**End of design.**
