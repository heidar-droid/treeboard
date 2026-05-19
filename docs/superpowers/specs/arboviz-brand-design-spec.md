# Arboviz Brand & Design Spec
> Saved 2026-05-19. Use this for all future Arboviz surfaces: landing page, marketing, docs, email.

## Identity

**Product name**: Arboviz  
**Logo treatment**: `arbo` (italic Fraunces, weight 300) + `viz` (Fraunces, weight 600, normal)  
**Tagline candidate**: "See your codebase come alive."

---

## Color Tokens

```css
/* Dark mode (default) */
--bg:        #06120c;   /* near-black forest */
--bg-2:      #0a1a12;   /* slightly lighter */
--ink:       #b6d4a7;   /* sage green — primary text */
--ink-muted: #7c8c75;   /* muted sage — secondary text */
--line:      rgba(182,212,167,.18);   /* subtle borders */
--line-2:    rgba(182,212,167,.32);   /* stronger borders */
--accent:    #b6d4a7;   /* = ink, used for interactive highlights */
--sage:      #b6d4a7;   /* canonical brand green */
--sage-glow: rgba(182,212,167,.55);  /* glow/halo effects */
--pop-bg:    rgba(8,14,11,.96);      /* card/popover background */
--shadow:    0 30px 60px -10px rgba(0,0,0,.7);
--grid:      rgba(182,212,167,.04);  /* dot grid texture */

/* Light mode overrides */
--bg:        #f6f4ee;
--bg-2:      #ecebe2;
--ink:       #1f2a23;
--ink-muted: #5d6b5a;
--accent:    #3f6b34;   /* deeper forest green for light bg */
--sage:      #3f6b34;
--pop-bg:    rgba(255,253,248,.96);
```

---

## Typography

| Role | Font | Weight | Size | Notes |
|---|---|---|---|---|
| Display / Logo | Fraunces | 300 (italic) + 600 | 22px+ | Serif, optical size 9–144 |
| Hero headings | Fraunces | 300 italic | 36–56px | Mixed italic/non-italic for emphasis |
| Body / UI | Geist Mono | 400–500 | 11–13px | Monospace, all UI copy |
| Labels / caps | Geist Mono | 400 | 9–10px | Uppercase, 2–3px letter-spacing |

**Anti-patterns**: Never Inter, Roboto, Space Grotesk, system-ui on display text.

---

## Background & Texture

```css
/* Body background — always both of these together */
background:
  radial-gradient(ellipse 800px 500px at 50% -100px, rgba(182,212,167,.07), transparent 70%),
  linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%);

/* Dot grid overlay — pseudo-element */
background-image: radial-gradient(circle at 1px 1px, rgba(182,212,167,.06) 1px, transparent 0);
background-size: 24px 24px;
```

---

## Cards & Surfaces

```css
/* Card — dark glass */
background: var(--pop-bg);
border: 1px solid var(--line-2);
border-radius: 28px;   /* Apple-style — --apple-radius */
box-shadow: var(--shadow), 0 0 0 1px rgba(182,212,167,.04);

/* Top-edge highlight (pseudo) */
::before {
  background: linear-gradient(90deg, transparent, var(--sage-glow), transparent);
  height: 1px; top: 0;
}
```

---

## Interactive Elements

```css
/* Primary button */
background: var(--sage);
color: #06120c;
border-radius: 10px;
font: 500 12px/1 'Geist Mono';
letter-spacing: 1px;
text-transform: uppercase;

/* Ghost button */
background: transparent;
border: 1px solid var(--line-2);
color: var(--ink-muted);

/* Input */
background: rgba(182,212,167,.04);
border: 1px solid var(--line);
border-radius: 10px;
color: var(--ink);
font: 400 13px 'Geist Mono';
```

---

## Canvas Nodes (SVG)

```
/* Root pill */
fill: #b6d4a7 (--sage);  rx = h/2;  h = 22px
label: Fraunces 600 12px, fill #0c1410

/* Folder pill */
fill: transparent;  stroke: rgba(182,212,167,.32);  stroke-width: 1;  rx = 11;  h = 22px
label: Geist Mono 500 10.5px, fill #cfe0c4 (--folder-lbl)

/* File pill */
fill: transparent;  stroke: rgba(182,212,167,.18);  stroke-width: 1;  rx = 9;  h = 18px
label: Geist Mono 400 9px, fill #6e7d6f (--file-lbl)

/* Edge (bezier) */
M{ax} {ay} C {ax} {my}, {bx} {my}, {bx} {by}
  ax/ay = bottom-center of parent pill
  bx/by = top-center of child pill
  my = midpoint Y
stroke: rgba(182,212,167,.18);  stroke-width: 1.4;  fill: none;  stroke-linecap: round;
```

---

## Motion

- Page load: staggered fade+translateY(10px) reveals, 0.35s ease
- Progress bar: left-to-right fill with sage glow: `box-shadow: 0 0 12px var(--sage-glow)`
- Theme transition: `transition: background-color 240ms ease, color 240ms ease`
- Hover on nodes: `transform: scale(1.07)` with stroke brightening
- Pulsing live indicator: `opacity 1 → 0.3 → 1` at 2s infinite

---

## Don'ts

- No purple gradients
- No white backgrounds with colored text (always dark bg or cream #f6f4ee)
- No Inter / Roboto / Arial
- No centered hero-only layouts (use asymmetric splits)
- No excessive rounded corners on small elements (inputs stay at 10px)
- No gradient buttons (flat sage fill only)
