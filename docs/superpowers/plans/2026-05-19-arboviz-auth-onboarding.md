# Arboviz Auth + Onboarding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone Next.js 15 web app at `personal projects/arboviz-web/` with Clerk auth, invite-only gate, 2-step onboarding, 8-slide product tour, and a CLI download page — deployed to Vercel.

**Architecture:** New Next.js 15 App Router project, completely separate from the Python CLI repo. All auth state lives in Clerk `publicMetadata` — no database needed. Middleware enforces the full access pipeline: signed-in → invite gate → onboarding → download.

**Tech Stack:** Next.js 15, TypeScript, Clerk, Tailwind CSS (layout only), CSS custom properties (all colors/design), Vercel

**Design spec:** `docs/superpowers/specs/arboviz-brand-design-spec.md`

---

## File Map

```
personal projects/arboviz-web/
├── app/
│   ├── layout.tsx                       ← ClerkProvider, fonts, globals.css
│   ├── globals.css                      ← Arboviz design tokens, background, dot grid
│   ├── page.tsx                         ← smart redirect
│   ├── sign-in/[[...sign-in]]/page.tsx  ← split layout + Clerk <SignIn>
│   ├── sign-up/[[...sign-up]]/page.tsx  ← split layout + Clerk <SignUp>
│   ├── invite/page.tsx                  ← invite code gate
│   ├── onboarding/page.tsx              ← steps 1 (name) + 2 (use case)
│   ├── onboarding/tour/page.tsx         ← 8-slide product tour
│   └── download/page.tsx                ← install page
├── actions/
│   ├── validate-invite.ts               ← server action: check code, set access_granted
│   └── complete-onboarding.ts           ← server action: save name+usecase, set onboarded
├── components/
│   ├── arboviz-tree.tsx                 ← animated SVG canvas (exact mockup geometry)
│   ├── tour-wizard.tsx                  ← 8-slide wizard with sidebar nav
│   └── copy-command.tsx                 ← copy-to-clipboard CLI command block
├── lib/
│   └── clerk-appearance.ts              ← shared Clerk appearance config object
├── middleware.ts                        ← Clerk auth + pipeline redirect logic
├── .env.local                           ← Clerk keys + INVITE_CODES (not committed)
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

---

## Task 1: Scaffold project + install deps

**Files:**
- Create: `personal projects/arboviz-web/` (via create-next-app)
- Create: `personal projects/arboviz-web/.env.local`

- [ ] **Step 1: Scaffold Next.js 15 app**

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects"
npx create-next-app@latest arboviz-web \
  --typescript \
  --tailwind \
  --app \
  --no-src-dir \
  --import-alias "@/*" \
  --eslint
```

When prompted: use App Router (default yes), skip Turbopack (no).

- [ ] **Step 2: Install Clerk**

```bash
cd arboviz-web
npm install @clerk/nextjs
```

- [ ] **Step 3: Create `.env.local`**

```bash
cat > .env.local << 'EOF'
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_REPLACE_ME
CLERK_SECRET_KEY=sk_test_REPLACE_ME
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/invite
INVITE_CODES=ARB-ALPHA,ARB-BETA01,ARB-DEMO01
EOF
```

**Note:** Replace `REPLACE_ME` values with real Clerk keys from https://dashboard.clerk.com after creating an Arboviz application there. Add `.env.local` to `.gitignore` (create-next-app does this automatically).

- [ ] **Step 4: Verify dev server starts**

```bash
npm run dev
```

Expected: server at http://localhost:3000 with default Next.js page.

- [ ] **Step 5: Commit scaffold**

```bash
git init
git add -A
git commit -m "chore: scaffold arboviz-web (Next.js 15 + Clerk)"
```

---

## Task 2: Global CSS + design tokens

**Files:**
- Modify: `app/globals.css`

- [ ] **Step 1: Replace globals.css with Arboviz design system**

Replace the entire contents of `app/globals.css` with:

```css
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;1,9..144,300&family=Geist+Mono:wght@300;400;500;600&display=swap');

@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg:         #06120c;
  --bg-2:       #0a1a12;
  --ink:        #b6d4a7;
  --ink-muted:  #7c8c75;
  --line:       rgba(182,212,167,.18);
  --line-2:     rgba(182,212,167,.32);
  --sage:       #b6d4a7;
  --sage-glow:  rgba(182,212,167,.55);
  --pop-bg:     rgba(8,14,11,.96);
  --shadow:     0 30px 60px -10px rgba(0,0,0,.8);
  --ar:         28px;
  --br:         10px;
}

* { box-sizing: border-box; }

html, body {
  background: var(--bg);
  color: var(--ink);
  font-family: 'Geist Mono', ui-monospace, SFMono-Regular, Menlo, monospace;
  -webkit-font-smoothing: antialiased;
  min-height: 100vh;
}

body {
  background:
    radial-gradient(ellipse 900px 500px at 50% -120px, rgba(182,212,167,.07) 0%, transparent 65%),
    linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%);
}

/* Dot grid texture */
body::before {
  content: '';
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  background-image: radial-gradient(circle at 1px 1px, rgba(182,212,167,.055) 1px, transparent 0);
  background-size: 24px 24px;
}

/* Shared card surface */
.arb-card {
  background: var(--pop-bg);
  border: 1px solid var(--line-2);
  border-radius: var(--ar);
  box-shadow: var(--shadow), 0 0 0 1px rgba(182,212,167,.04);
  position: relative;
  overflow: hidden;
}

.arb-card::before {
  content: '';
  position: absolute;
  top: 0; left: 10%; right: 10%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--sage-glow), transparent);
}

/* Buttons */
.arb-btn-primary {
  width: 100%;
  padding: 14px;
  border-radius: var(--br);
  background: var(--sage);
  color: #06120c;
  border: none;
  cursor: pointer;
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  transition: filter .2s, transform .15s;
}
.arb-btn-primary:hover { filter: brightness(1.1); transform: translateY(-1px); }

.arb-btn-ghost {
  width: 100%;
  padding: 12px;
  border-radius: var(--br);
  background: rgba(182,212,167,.06);
  border: 1px solid var(--line);
  color: var(--ink);
  cursor: pointer;
  font-family: 'Geist Mono', monospace;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 9px;
  transition: border-color .2s, background .2s;
}
.arb-btn-ghost:hover { border-color: var(--line-2); background: rgba(182,212,167,.1); }

/* Inputs */
.arb-input {
  width: 100%;
  padding: 13px 15px;
  border-radius: var(--br);
  background: rgba(182,212,167,.05);
  border: 1px solid var(--line);
  color: var(--ink);
  font-family: 'Geist Mono', monospace;
  font-size: 13px;
  outline: none;
  transition: border-color .2s, box-shadow .2s;
}
.arb-input:focus {
  border-color: var(--line-2);
  box-shadow: 0 0 0 3px rgba(182,212,167,.08);
}
.arb-input::placeholder { color: var(--ink-muted); }

/* Label */
.arb-label {
  font-size: 10px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--ink-muted);
  margin-bottom: 8px;
  display: block;
}

/* Logo */
.arb-logo {
  font-family: 'Fraunces', serif;
  font-weight: 300;
  font-style: italic;
  font-size: 22px;
  color: var(--sage);
  letter-spacing: -.3px;
}
.arb-logo strong { font-style: normal; font-weight: 600; }

/* Divider */
.arb-divider {
  display: flex;
  align-items: center;
  gap: 14px;
  margin: 18px 0;
  font-size: 10px;
  color: var(--ink-muted);
}
.arb-divider::before,
.arb-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--line);
}

/* Progress indicator dots */
.arb-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 34px;
}
.arb-pdot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--line-2);
  transition: all .3s;
}
.arb-pdot[data-active="true"] {
  background: var(--sage);
  width: 20px;
  border-radius: 3px;
  box-shadow: 0 0 8px var(--sage-glow);
}
.arb-pdot[data-done="true"] { background: rgba(182,212,167,.5); }
```

- [ ] **Step 2: Verify dev server still compiles**

```bash
npm run dev
```

Expected: compiles without errors.

- [ ] **Step 3: Commit**

```bash
git add app/globals.css
git commit -m "feat: add Arboviz design tokens and CSS utilities"
```

---

## Task 3: Root layout + Clerk provider

**Files:**
- Modify: `app/layout.tsx`

- [ ] **Step 1: Replace app/layout.tsx**

```tsx
// app/layout.tsx
import type { Metadata } from 'next';
import { ClerkProvider } from '@clerk/nextjs';
import './globals.css';

export const metadata: Metadata = {
  title: 'Arboviz',
  description: 'See your codebase come alive.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <ClerkProvider>
      <html lang="en">
        <body style={{ position: 'relative', zIndex: 1 }}>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
```

- [ ] **Step 2: Verify build**

```bash
npm run build 2>&1 | tail -20
```

Expected: build succeeds (may warn about missing Clerk keys — that's fine for now).

- [ ] **Step 3: Commit**

```bash
git add app/layout.tsx
git commit -m "feat: add ClerkProvider to root layout"
```

---

## Task 4: Middleware

**Files:**
- Create: `middleware.ts`

- [ ] **Step 1: Create middleware.ts**

```ts
// middleware.ts
import { clerkMiddleware } from '@clerk/nextjs/server';
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

type PublicMeta = {
  access_granted?: boolean;
  onboarded?: boolean;
};

export default clerkMiddleware(async (auth, req: NextRequest) => {
  const { userId, sessionClaims } = await auth();
  const path = req.nextUrl.pathname;
  const pub = (sessionClaims?.publicMetadata ?? {}) as PublicMeta;

  const publicPaths = ['/sign-in', '/sign-up'];
  if (publicPaths.some(p => path.startsWith(p))) return NextResponse.next();

  if (!userId) {
    return NextResponse.redirect(new URL('/sign-in', req.url));
  }

  if (!pub.access_granted && !path.startsWith('/invite')) {
    return NextResponse.redirect(new URL('/invite', req.url));
  }

  if (pub.access_granted && !pub.onboarded &&
      !path.startsWith('/onboarding')) {
    return NextResponse.redirect(new URL('/onboarding', req.url));
  }

  if (pub.onboarded &&
      (path.startsWith('/invite') || path.startsWith('/onboarding'))) {
    return NextResponse.redirect(new URL('/download', req.url));
  }

  return NextResponse.next();
});

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|.*\\..*).*)'],
};
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit 2>&1 | head -20
```

Expected: no errors (or only missing env var warnings, not type errors).

- [ ] **Step 3: Commit**

```bash
git add middleware.ts
git commit -m "feat: add Clerk auth middleware with pipeline redirects"
```

---

## Task 5: Clerk appearance config

**Files:**
- Create: `lib/clerk-appearance.ts`

- [ ] **Step 1: Create shared appearance config**

```ts
// lib/clerk-appearance.ts
import type { Appearance } from '@clerk/types';

export const clerkAppearance: Appearance = {
  variables: {
    colorPrimary: '#b6d4a7',
    colorBackground: 'rgba(8,14,11,.96)',
    colorInputBackground: 'rgba(182,212,167,.05)',
    colorInputText: '#b6d4a7',
    colorText: '#b6d4a7',
    colorTextSecondary: '#7c8c75',
    colorNeutral: '#7c8c75',
    borderRadius: '10px',
    fontFamily: '"Geist Mono", ui-monospace, monospace',
    fontSize: '13px',
  },
  elements: {
    rootBox: { width: '100%' },
    card: {
      background: 'transparent',
      boxShadow: 'none',
      border: 'none',
      padding: '0',
    },
    headerTitle: {
      fontFamily: '"Fraunces", serif',
      fontWeight: '300',
      fontStyle: 'italic',
      fontSize: '24px',
      color: '#b6d4a7',
    },
    formButtonPrimary: {
      background: '#b6d4a7',
      color: '#06120c',
      fontWeight: '600',
      letterSpacing: '1.5px',
      textTransform: 'uppercase',
    },
    socialButtonsBlockButton: {
      background: 'rgba(182,212,167,.06)',
      border: '1px solid rgba(182,212,167,.18)',
      color: '#b6d4a7',
    },
    dividerLine: { background: 'rgba(182,212,167,.18)' },
    dividerText: { color: '#7c8c75' },
    footerActionLink: { color: '#b6d4a7' },
    identityPreviewText: { color: '#b6d4a7' },
    formFieldInput: {
      background: 'rgba(182,212,167,.05)',
      border: '1px solid rgba(182,212,167,.18)',
      color: '#b6d4a7',
    },
    formFieldLabel: {
      color: '#7c8c75',
      textTransform: 'uppercase',
      letterSpacing: '1.5px',
      fontSize: '10px',
    },
  },
};
```

- [ ] **Step 2: Commit**

```bash
git add lib/clerk-appearance.ts
git commit -m "feat: add Clerk appearance config (Arboviz design system)"
```

---

## Task 6: ArbovizTree SVG component

**Files:**
- Create: `components/arboviz-tree.tsx`

- [ ] **Step 1: Create ArbovizTree component**

The SVG uses exact geometry from the real Arboviz render engine:
- Bezier edges: `M{ax} {ay} C {ax} {my}, {bx} {my}, {bx} {by}` (bottom-center parent → top-center child)
- Root pill: `fill #b6d4a7`, `h=22`, `rx=11`
- Folder pills: `stroke rgba(182,212,167,.32)`, `h=22`, `rx=11`
- File pills: `stroke rgba(182,212,167,.18)`, `h=18`, `rx=9`

```tsx
// components/arboviz-tree.tsx
'use client';

export function ArbovizTree() {
  return (
    <svg
      viewBox="0 0 270 210"
      width="270"
      height="210"
      style={{ overflow: 'visible' }}
    >
      <defs>
        <style>{`
          .arb-edge { stroke:rgba(182,212,167,.22); stroke-width:1.4; fill:none; stroke-linecap:round;
            stroke-dasharray:200; stroke-dashoffset:200;
            animation: arb-draw 1s ease forwards; }
          .arb-edge:nth-child(1){animation-delay:.05s}
          .arb-edge:nth-child(2){animation-delay:.12s}
          .arb-edge:nth-child(3){animation-delay:.3s}
          .arb-edge:nth-child(4){animation-delay:.38s}
          .arb-edge:nth-child(5){animation-delay:.38s}
          @keyframes arb-draw { to { stroke-dashoffset: 0; } }

          .arb-pill { animation: arb-pop .4s ease both; }
          .arb-pill:nth-child(6){animation-delay:0s}
          .arb-pill:nth-child(7){animation-delay:.04s}
          .arb-pill:nth-child(8){animation-delay:.2s}
          .arb-pill:nth-child(9){animation-delay:.22s}
          .arb-pill:nth-child(10){animation-delay:.42s}
          .arb-pill:nth-child(11){animation-delay:.44s}
          .arb-pill:nth-child(12){animation-delay:.44s}
          @keyframes arb-pop { from{opacity:0;transform:scale(.88)} to{opacity:1;transform:scale(1)} }

          .arb-lbl { animation: arb-fadein .35s ease both; }
          .arb-lbl:nth-of-type(1){animation-delay:.08s}
          .arb-lbl:nth-of-type(2){animation-delay:.25s}
          .arb-lbl:nth-of-type(3){animation-delay:.27s}
          .arb-lbl:nth-of-type(4){animation-delay:.45s}
          .arb-lbl:nth-of-type(5){animation-delay:.47s}
          .arb-lbl:nth-of-type(6){animation-delay:.47s}
          @keyframes arb-fadein { from{opacity:0} to{opacity:1} }
        `}</style>
      </defs>

      {/* Bezier edges */}
      {/* root(cx=130,bot=32) → src(cx=78,top=94) my=63 */}
      <path className="arb-edge" d="M130 32 C 130 63, 78 63, 78 94" />
      {/* root → tests(cx=210,top=94) */}
      <path className="arb-edge" d="M130 32 C 130 63, 210 63, 210 94" />
      {/* src(cx=78,bot=116) → server.py(cx=46,top=172) */}
      <path className="arb-edge" d="M78 116 C 78 144, 46 144, 46 172" />
      {/* src → cli.py(cx=130,top=172) */}
      <path className="arb-edge" d="M78 116 C 78 144, 130 144, 130 172" />
      {/* tests(cx=210,bot=116) → scan.py(cx=218,top=172) */}
      <path className="arb-edge" d="M210 116 C 210 144, 218 144, 218 172" />

      {/* Root pill: x=80 y=10 w=100 h=22 rx=11 — filled sage */}
      <rect className="arb-pill" x={80} y={10} width={100} height={22} rx={11} fill="#b6d4a7" />
      {/* Folder: src x=49 y=94 w=58 h=22 rx=11 */}
      <rect className="arb-pill" x={49} y={94} width={58} height={22} rx={11}
        fill="transparent" stroke="rgba(182,212,167,.32)" strokeWidth={1} />
      {/* Folder: tests x=176 y=94 w=68 h=22 rx=11 */}
      <rect className="arb-pill" x={176} y={94} width={68} height={22} rx={11}
        fill="transparent" stroke="rgba(182,212,167,.32)" strokeWidth={1} />
      {/* File: server.py x=2 y=172 w=88 h=18 rx=9 */}
      <rect className="arb-pill" x={2} y={172} width={88} height={18} rx={9}
        fill="transparent" stroke="rgba(182,212,167,.18)" strokeWidth={1} />
      {/* File: cli.py x=96 y=172 w=68 h=18 rx=9 */}
      <rect className="arb-pill" x={96} y={172} width={68} height={18} rx={9}
        fill="transparent" stroke="rgba(182,212,167,.18)" strokeWidth={1} />
      {/* File: scan.py x=181 y=172 w=75 h=18 rx=9 */}
      <rect className="arb-pill" x={181} y={172} width={75} height={18} rx={9}
        fill="transparent" stroke="rgba(182,212,167,.18)" strokeWidth={1} />

      {/* Labels */}
      <text className="arb-lbl" x={130} y={25} textAnchor="middle"
        fill="#0c1410" fontFamily="'Fraunces', serif" fontWeight={600} fontSize={12}>
        my-project
      </text>
      <text className="arb-lbl" x={78} y={108} textAnchor="middle"
        fill="#cfe0c4" fontFamily="'Geist Mono', monospace" fontWeight={500} fontSize={10.5}>
        src
      </text>
      <text className="arb-lbl" x={210} y={108} textAnchor="middle"
        fill="#cfe0c4" fontFamily="'Geist Mono', monospace" fontWeight={500} fontSize={10.5}>
        tests
      </text>
      <text className="arb-lbl" x={46} y={184} textAnchor="middle"
        fill="#6e7d6f" fontFamily="'Geist Mono', monospace" fontWeight={400} fontSize={9}>
        server.py
      </text>
      <text className="arb-lbl" x={130} y={184} textAnchor="middle"
        fill="#6e7d6f" fontFamily="'Geist Mono', monospace" fontWeight={400} fontSize={9}>
        cli.py
      </text>
      <text className="arb-lbl" x={218} y={184} textAnchor="middle"
        fill="#6e7d6f" fontFamily="'Geist Mono', monospace" fontWeight={400} fontSize={9}>
        scan.py
      </text>
    </svg>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add components/arboviz-tree.tsx
git commit -m "feat: ArbovizTree SVG component with bezier edges"
```

---

## Task 7: Sign-in + Sign-up pages

**Files:**
- Create: `app/sign-in/[[...sign-in]]/page.tsx`
- Create: `app/sign-up/[[...sign-up]]/page.tsx`

- [ ] **Step 1: Create sign-in page**

```tsx
// app/sign-in/[[...sign-in]]/page.tsx
import { SignIn } from '@clerk/nextjs';
import { ArbovizTree } from '@/components/arboviz-tree';
import { clerkAppearance } from '@/lib/clerk-appearance';

export default function SignInPage() {
  return (
    <main style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', padding: '40px', position: 'relative', zIndex: 1,
    }}>
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 400px', gap: '64px',
        maxWidth: '860px', width: '100%', alignItems: 'center',
      }}>
        {/* Hero */}
        <div>
          <div className="arb-logo" style={{ marginBottom: '28px' }}>
            arbo<strong>viz</strong>
          </div>
          <h1 style={{
            fontFamily: "'Fraunces', serif", fontWeight: 300, fontStyle: 'italic',
            fontSize: 'clamp(36px, 5vw, 52px)', lineHeight: 1.05,
            color: 'var(--ink)', marginBottom: '18px',
          }}>
            See your<br />codebase<br />
            <em style={{ fontStyle: 'normal', color: 'var(--sage)', display: 'block' }}>
              come alive.
            </em>
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--ink-muted)', lineHeight: 1.9, maxWidth: '340px' }}>
            A visual canvas for your entire project tree. Open files, explore
            structure, and navigate your code the way it was meant to be seen.
          </p>
          <div style={{ marginTop: '44px' }}>
            <ArbovizTree />
          </div>
        </div>

        {/* Card */}
        <div className="arb-card" style={{ padding: '38px' }}>
          <div className="arb-logo" style={{ marginBottom: '26px', display: 'block' }}>
            arbo<strong>viz</strong>
          </div>
          <SignIn appearance={clerkAppearance} />
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 2: Create sign-up page**

```tsx
// app/sign-up/[[...sign-up]]/page.tsx
import { SignUp } from '@clerk/nextjs';
import { ArbovizTree } from '@/components/arboviz-tree';
import { clerkAppearance } from '@/lib/clerk-appearance';

export default function SignUpPage() {
  return (
    <main style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', padding: '40px', position: 'relative', zIndex: 1,
    }}>
      <div style={{
        display: 'grid', gridTemplateColumns: '1fr 400px', gap: '64px',
        maxWidth: '860px', width: '100%', alignItems: 'center',
      }}>
        <div>
          <div className="arb-logo" style={{ marginBottom: '28px' }}>
            arbo<strong>viz</strong>
          </div>
          <h1 style={{
            fontFamily: "'Fraunces', serif", fontWeight: 300, fontStyle: 'italic',
            fontSize: 'clamp(36px, 5vw, 52px)', lineHeight: 1.05,
            color: 'var(--ink)', marginBottom: '18px',
          }}>
            See your<br />codebase<br />
            <em style={{ fontStyle: 'normal', color: 'var(--sage)', display: 'block' }}>
              come alive.
            </em>
          </h1>
          <p style={{ fontSize: '12px', color: 'var(--ink-muted)', lineHeight: 1.9, maxWidth: '340px' }}>
            A visual canvas for your entire project tree. Open files, explore
            structure, and navigate your code the way it was meant to be seen.
          </p>
          <div style={{ marginTop: '44px' }}>
            <ArbovizTree />
          </div>
        </div>
        <div className="arb-card" style={{ padding: '38px' }}>
          <div className="arb-logo" style={{ marginBottom: '26px', display: 'block' }}>
            arbo<strong>viz</strong>
          </div>
          <SignUp appearance={clerkAppearance} />
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
npx tsc --noEmit 2>&1 | head -30
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add app/sign-in app/sign-up
git commit -m "feat: sign-in and sign-up pages with Arboviz split layout"
```

---

## Task 8: Invite code gate

**Files:**
- Create: `actions/validate-invite.ts`
- Create: `app/invite/page.tsx`

- [ ] **Step 1: Create validate-invite server action**

```ts
// actions/validate-invite.ts
'use server';

import { auth, clerkClient } from '@clerk/nextjs/server';

export async function validateInvite(
  formData: FormData,
): Promise<{ success: boolean; error?: string }> {
  const { userId } = await auth();
  if (!userId) return { success: false, error: 'Not authenticated' };

  const code = (formData.get('code') as string ?? '').trim().toUpperCase();
  if (!code) return { success: false, error: 'Please enter your invite code' };

  const validCodes = (process.env.INVITE_CODES ?? '')
    .split(',')
    .map(c => c.trim().toUpperCase())
    .filter(Boolean);

  if (!validCodes.includes(code)) {
    return { success: false, error: 'Invalid invite code. Try again or request access.' };
  }

  const client = await clerkClient();
  await client.users.updateUserMetadata(userId, {
    publicMetadata: { access_granted: true },
  });

  return { success: true };
}
```

- [ ] **Step 2: Create invite gate page**

```tsx
// app/invite/page.tsx
'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { validateInvite } from '@/actions/validate-invite';

export default function InvitePage() {
  const [error, setError] = useState('');
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError('');
    const formData = new FormData(e.currentTarget);
    startTransition(async () => {
      const result = await validateInvite(formData);
      if (result.success) {
        router.push('/onboarding');
        router.refresh();
      } else {
        setError(result.error ?? 'Something went wrong');
      }
    });
  }

  return (
    <main style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', position: 'relative', zIndex: 1,
    }}>
      <div className="arb-card" style={{ padding: '52px 46px', width: '460px', textAlign: 'center' }}>

        {/* Live badge */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: '8px',
          padding: '5px 14px', borderRadius: '20px',
          border: '1px solid rgba(182,212,167,.3)', background: 'rgba(182,212,167,.06)',
          fontSize: '9px', letterSpacing: '3px', textTransform: 'uppercase',
          color: 'var(--sage)', marginBottom: '30px',
        }}>
          <span style={{
            width: '6px', height: '6px', borderRadius: '50%', background: 'var(--sage)',
            animation: 'arbBlink 2s infinite',
          }} />
          Early Access
        </div>

        <div className="arb-logo" style={{ display: 'block', marginBottom: '20px', textAlign: 'center' }}>
          arbo<strong>viz</strong>
        </div>

        <h2 style={{
          fontFamily: "'Fraunces', serif", fontWeight: 300, fontStyle: 'italic',
          fontSize: '28px', color: 'var(--ink)', marginBottom: '10px',
        }}>
          You need an invite.
        </h2>
        <p style={{ fontSize: '12px', color: 'var(--ink-muted)', lineHeight: 1.8, marginBottom: '32px' }}>
          Arboviz is currently in private beta.<br />
          Enter your invite code to continue.
        </p>

        <form onSubmit={handleSubmit}>
          <input
            name="code"
            type="text"
            placeholder="ARB-XXXXX"
            maxLength={9}
            autoComplete="off"
            spellCheck={false}
            style={{
              width: '100%', padding: '18px', borderRadius: 'var(--br)',
              background: 'rgba(182,212,167,.04)',
              border: error ? '1px solid #e06060' : '1px solid var(--line-2)',
              color: 'var(--sage)',
              fontFamily: "'Geist Mono', monospace",
              fontSize: '20px', fontWeight: 500, letterSpacing: '8px',
              textAlign: 'center', outline: 'none', textTransform: 'uppercase',
              marginBottom: '6px',
            }}
          />

          {error && (
            <p style={{ fontSize: '11px', color: '#e06060', marginBottom: '12px', textAlign: 'left' }}>
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isPending}
            className="arb-btn-primary"
            style={{ marginTop: '8px', opacity: isPending ? .6 : 1 }}
          >
            {isPending ? 'Checking…' : 'Unlock Access'}
          </button>
        </form>

        <p style={{ fontSize: '11px', color: 'var(--ink-muted)', marginTop: '18px' }}>
          No code?{' '}
          <a href="mailto:hello@arboviz.com" style={{ color: 'var(--sage)', textDecoration: 'none' }}>
            Request early access →
          </a>
        </p>
      </div>

      <style>{`
        @keyframes arbBlink { 0%,100%{opacity:1} 50%{opacity:.25} }
      `}</style>
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add actions/validate-invite.ts app/invite/page.tsx
git commit -m "feat: invite code gate with server action validation"
```

---

## Task 9: Onboarding wizard (name + use case)

**Files:**
- Create: `actions/complete-onboarding.ts`
- Create: `app/onboarding/page.tsx`

- [ ] **Step 1: Create complete-onboarding server action**

```ts
// actions/complete-onboarding.ts
'use server';

import { auth, clerkClient } from '@clerk/nextjs/server';

type UseCaseValue = 'solo' | 'team' | 'oss';

export async function completeOnboarding(
  formData: FormData,
): Promise<{ success: boolean; error?: string }> {
  const { userId } = await auth();
  if (!userId) return { success: false, error: 'Not authenticated' };

  const name = (formData.get('name') as string ?? '').trim();
  const useCase = formData.get('use_case') as UseCaseValue | null;

  if (!name) return { success: false, error: 'Please enter your name' };
  if (!useCase) return { success: false, error: 'Please select a use case' };

  const client = await clerkClient();
  await client.users.updateUser(userId, { firstName: name });
  await client.users.updateUserMetadata(userId, {
    publicMetadata: {
      access_granted: true,
      display_name: name,
      use_case: useCase,
      onboarded: true,
    },
  });

  return { success: true };
}
```

- [ ] **Step 2: Create onboarding page**

```tsx
// app/onboarding/page.tsx
'use client';

import { useState, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { completeOnboarding } from '@/actions/complete-onboarding';

type UseCase = 'solo' | 'team' | 'oss';

const USE_CASES: { value: UseCase; icon: string; title: string; sub: string }[] = [
  { value: 'solo',  icon: '🌱', title: 'Solo developer',     sub: 'Personal projects, side projects, learning' },
  { value: 'team',  icon: '🌿', title: 'Team / professional', sub: 'Work codebases, team collaboration' },
  { value: 'oss',   icon: '🌳', title: 'Open source',         sub: 'Contributing to or maintaining OSS projects' },
];

export default function OnboardingPage() {
  const [step, setStep] = useState<1 | 2>(1);
  const [name, setName] = useState('');
  const [useCase, setUseCase] = useState<UseCase | null>(null);
  const [error, setError] = useState('');
  const [isPending, startTransition] = useTransition();
  const router = useRouter();

  function handleNameNext(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError('Please enter your name'); return; }
    setError('');
    setStep(2);
  }

  function handleFinalSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!useCase) { setError('Please select one'); return; }
    setError('');
    const fd = new FormData();
    fd.set('name', name);
    fd.set('use_case', useCase);
    startTransition(async () => {
      const result = await completeOnboarding(fd);
      if (result.success) {
        router.push('/onboarding/tour');
        router.refresh();
      } else {
        setError(result.error ?? 'Something went wrong');
      }
    });
  }

  return (
    <main style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', position: 'relative', zIndex: 1,
    }}>
      <div className="arb-card" style={{ padding: '46px', width: '500px' }}>

        {/* Progress dots */}
        <div className="arb-progress">
          <div className="arb-pdot" data-active={step === 1 ? 'true' : undefined} data-done={step === 2 ? 'true' : undefined} />
          <div className="arb-pdot" data-active={step === 2 ? 'true' : undefined} />
          <span style={{ fontSize: '9px', color: 'var(--ink-muted)', letterSpacing: '2px', textTransform: 'uppercase', marginLeft: 'auto' }}>
            Step {step} of 2
          </span>
        </div>

        {step === 1 && (
          <form onSubmit={handleNameNext}>
            <h2 style={{
              fontFamily: "'Fraunces', serif", fontWeight: 300, fontStyle: 'italic',
              fontSize: '28px', color: 'var(--ink)', marginBottom: '8px', lineHeight: 1.2,
            }}>
              What should we<br />call you?
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '28px', lineHeight: 1.7 }}>
              Just what you go by. We'll use this to personalise your experience.
            </p>
            <div style={{ marginBottom: '26px' }}>
              <label className="arb-label">Preferred name</label>
              <input
                className="arb-input"
                type="text"
                placeholder="e.g. Heidar"
                value={name}
                onChange={e => setName(e.target.value)}
                autoFocus
                style={{ fontSize: '16px', padding: '16px' }}
              />
            </div>
            {error && <p style={{ fontSize: '11px', color: '#e06060', marginBottom: '10px' }}>{error}</p>}
            <button type="submit" className="arb-btn-primary">Continue</button>
          </form>
        )}

        {step === 2 && (
          <form onSubmit={handleFinalSubmit}>
            <h2 style={{
              fontFamily: "'Fraunces', serif", fontWeight: 300, fontStyle: 'italic',
              fontSize: '28px', color: 'var(--ink)', marginBottom: '8px', lineHeight: 1.2,
            }}>
              How will you use<br />Arboviz?
            </h2>
            <p style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '22px', lineHeight: 1.7 }}>
              Pick the one that fits best.
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '9px', marginBottom: '26px' }}>
              {USE_CASES.map(uc => (
                <button
                  key={uc.value}
                  type="button"
                  onClick={() => setUseCase(uc.value)}
                  style={{
                    padding: '15px 17px', borderRadius: 'var(--br)', textAlign: 'left',
                    display: 'flex', alignItems: 'center', gap: '13px', cursor: 'pointer',
                    background: useCase === uc.value ? 'rgba(182,212,167,.1)' : 'rgba(182,212,167,.03)',
                    border: useCase === uc.value ? '1px solid var(--sage)' : '1px solid var(--line)',
                    transition: 'all .2s',
                    width: '100%',
                  }}
                >
                  <span style={{ fontSize: '20px', flexShrink: 0 }}>{uc.icon}</span>
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)', marginBottom: '2px' }}>{uc.title}</div>
                    <div style={{ fontSize: '10px', color: 'var(--ink-muted)' }}>{uc.sub}</div>
                  </div>
                </button>
              ))}
            </div>

            {error && <p style={{ fontSize: '11px', color: '#e06060', marginBottom: '10px' }}>{error}</p>}
            <button
              type="submit"
              disabled={isPending || !useCase}
              className="arb-btn-primary"
              style={{ opacity: (isPending || !useCase) ? .6 : 1 }}
            >
              {isPending ? 'Saving…' : "Let's go →"}
            </button>
          </form>
        )}
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add actions/complete-onboarding.ts app/onboarding/page.tsx
git commit -m "feat: onboarding wizard (name + use case, 2 steps)"
```

---

## Task 10: Product tour

**Files:**
- Create: `components/tour-wizard.tsx`
- Create: `app/onboarding/tour/page.tsx`

- [ ] **Step 1: Create TourWizard component**

```tsx
// components/tour-wizard.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ArbovizTree } from './arboviz-tree';

const SLIDES = [
  {
    tag: 'Feature 01 — Canvas',
    title: 'Your project, mapped.',
    desc: 'Every folder and file in your project renders as an interactive node on an infinite canvas. Expand folders, collapse branches, and see your entire codebase at once.',
    visual: 'canvas',
  },
  {
    tag: 'Feature 02 — Navigation',
    title: 'Move like you mean it.',
    desc: 'Scroll to zoom in and out. Click and drag the canvas background to pan. Works exactly like Figma or Google Maps — completely natural from day one.',
    visual: 'navigate',
  },
  {
    tag: 'Feature 03 — File Cards',
    title: 'Click to see inside.',
    desc: 'Click any file node to open a detail card showing its content, size, language, and last modified time. Up to two cards can be open at once, draggable anywhere.',
    visual: 'popover',
  },
  {
    tag: 'Feature 04 — Resize',
    title: 'Make it your size.',
    desc: 'Cards open full-size by default. Drag the bottom-right corner handle to resize freely — compact for a quick peek, full-height for reading the whole file.',
    visual: 'resize',
  },
  {
    tag: 'Feature 05 — Pin Bar',
    title: 'Keep the important stuff close.',
    desc: 'Pin any file to the bar at the top. Click a chip to instantly open that file\'s card — no hunting through the canvas.',
    visual: 'pins',
  },
  {
    tag: 'Feature 06 — Control Center',
    title: 'Every tool, one panel.',
    desc: 'The left control panel gives you access to all views and modes: tree view, heatmap, import graph, content search, and theme toggle.',
    visual: 'cc',
  },
  {
    tag: 'Feature 07 — Git Mode',
    title: 'See what changed.',
    desc: 'Toggle git mode to overlay uncommitted changes onto the canvas. Modified files glow orange, new files green, deleted files red. Click any to see the full diff.',
    visual: 'git',
  },
  {
    tag: 'Feature 08 — Project Tabs',
    title: 'Multiple projects, zero friction.',
    desc: 'Click + to open another folder in a new tab. Each tab runs its own Arboviz instance. Switch between projects instantly — exactly like browser tabs.',
    visual: 'tabs',
  },
] as const;

function SlideVisual({ type }: { type: typeof SLIDES[number]['visual'] }) {
  const s: React.CSSProperties = {
    flex: 1, background: 'rgba(6,18,12,.7)', borderRadius: '14px',
    border: '1px solid var(--line)', overflow: 'hidden', position: 'relative',
    display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '20px',
  };

  if (type === 'canvas') return (
    <div style={s}><ArbovizTree /></div>
  );

  if (type === 'navigate') return (
    <div style={s}>
      <div style={{ display: 'flex', gap: '36px' }}>
        {[
          { icon: '🖱', key: 'Scroll', desc: 'Zoom in / out' },
          { icon: '✋', key: 'Drag', desc: 'Pan the canvas' },
          { icon: '👆', key: 'Click folder', desc: 'Expand / collapse' },
        ].map(n => (
          <div key={n.key} style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '32px', marginBottom: '9px' }}>{n.icon}</div>
            <div style={{ fontSize: '9px', color: 'var(--sage)', letterSpacing: '2px', textTransform: 'uppercase', marginBottom: '4px' }}>{n.key}</div>
            <div style={{ fontSize: '10px', color: 'var(--ink-muted)' }}>{n.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );

  if (type === 'popover') return (
    <div style={s}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '5px 13px', borderRadius: '18px', border: '1px solid rgba(182,212,167,.18)', fontSize: '10px', color: '#6e7d6f' }}>◦ server.py</div>
        <div style={{ color: 'var(--sage)', fontSize: '16px', opacity: .7 }}>→</div>
        <div style={{ width: '210px', background: 'rgba(8,14,11,.98)', border: '1px solid var(--sage)', borderRadius: '12px', overflow: 'hidden' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🐍</span><span style={{ fontSize: '9px', color: 'var(--ink-muted)', flex: 1 }}>src/server.py</span><span style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>✕</span>
          </div>
          <div style={{ padding: '12px' }}>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)', marginBottom: '4px' }}>server.py</div>
            <div style={{ fontSize: '9px', color: 'var(--ink-muted)', marginBottom: '10px' }}>14 KB · Python · 2h ago</div>
            {[90, 72, 85, 60].map((w, i) => (
              <div key={i} style={{ height: '5px', borderRadius: '2px', background: 'var(--line)', marginBottom: '5px', width: `${w}%` }} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );

  if (type === 'resize') return (
    <div style={s}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
        <div style={{ width: '180px', background: 'rgba(8,14,11,.98)', border: '1px solid var(--sage)', borderRadius: '12px', overflow: 'hidden', position: 'relative' }}>
          <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--line)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span>🐍</span><span style={{ fontSize: '9px', color: 'var(--ink-muted)', flex: 1 }}>server.py</span><span style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>✕</span>
          </div>
          <div style={{ padding: '12px' }}>
            {[90, 70, 82, 55].map((w, i) => (
              <div key={i} style={{ height: '5px', borderRadius: '2px', background: 'var(--line)', marginBottom: '5px', width: `${w}%` }} />
            ))}
          </div>
          <div style={{ position: 'absolute', bottom: '5px', right: '5px', width: '14px', height: '14px', borderRight: '2px solid var(--sage)', borderBottom: '2px solid var(--sage)', borderRadius: '0 0 4px 0' }} />
        </div>
        <p style={{ fontSize: '11px', color: 'var(--ink-muted)', maxWidth: '120px', lineHeight: 1.6 }}>Drag the ↘ corner to resize freely</p>
      </div>
    </div>
  );

  if (type === 'pins') return (
    <div style={{ ...s, flexDirection: 'column', gap: '14px' }}>
      <div style={{ display: 'flex', gap: '7px', flexWrap: 'wrap', background: 'rgba(8,14,11,.96)', padding: '10px 14px', borderRadius: '10px', border: '1px solid var(--line)', width: '100%' }}>
        {['📌 server.py', '📌 index.html', '📌 cli.py'].map(c => (
          <span key={c} style={{ padding: '4px 10px', borderRadius: '12px', background: 'rgba(182,212,167,.08)', border: '1px solid var(--sage)', fontSize: '10px', color: 'var(--sage)' }}>{c}</span>
        ))}
        <span style={{ padding: '4px 10px', borderRadius: '12px', border: '1px solid var(--line)', fontSize: '10px', color: 'var(--ink-muted)' }}>+ Pin</span>
      </div>
      <p style={{ fontSize: '11px', color: 'var(--ink-muted)', textAlign: 'center' }}>Sits right below the tab bar — always reachable</p>
    </div>
  );

  if (type === 'cc') return (
    <div style={{ ...s, padding: '20px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '9px', width: '100%' }}>
        {[
          { icon: '🌳', label: 'Tree View', sub: 'Default — project structure', active: true },
          { icon: '🔥', label: 'Heatmap', sub: 'File activity over time' },
          { icon: '🔗', label: 'Import Graph', sub: 'File dependency relationships' },
          { icon: '🔍', label: 'Search', sub: 'Search inside all files' },
          { icon: '☾', label: 'Theme Toggle', sub: 'Dark / light mode' },
        ].map(item => (
          <div key={item.label} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <div style={{
              width: '32px', height: '32px', borderRadius: '8px', flexShrink: 0,
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '14px',
              background: item.active ? 'rgba(182,212,167,.18)' : 'rgba(182,212,167,.07)',
              border: item.active ? '1px solid var(--sage)' : '1px solid var(--line)',
            }}>{item.icon}</div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--ink)' }}>{item.label}</div>
              <div style={{ fontSize: '9px', color: 'var(--ink-muted)' }}>{item.sub}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );

  if (type === 'git') return (
    <div style={{ ...s, flexDirection: 'column', alignItems: 'flex-start', padding: '24px', gap: '0' }}>
      {[
        { name: 'server.py', badge: 'MODIFIED', cls: 'rgba(240,136,62,.5)', color: '#f0883e', bg: 'rgba(240,136,62,.2)' },
        { name: 'new-feature.py', badge: 'ADDED', cls: 'rgba(182,212,167,.5)', color: 'var(--sage)', bg: 'rgba(182,212,167,.2)' },
        { name: 'old-util.py', badge: 'DELETED', cls: 'rgba(200,80,80,.4)', color: '#e06060', bg: 'rgba(200,80,80,.15)', opacity: .7 },
      ].map(n => (
        <div key={n.name} style={{ display: 'inline-flex', alignItems: 'center', gap: '9px', padding: '6px 14px', borderRadius: '20px', fontSize: '11px', border: `1px solid ${n.cls}`, color: n.color, marginBottom: '9px', opacity: n.opacity }}>
          <span>{n.name}</span>
          <span style={{ fontSize: '8px', padding: '1px 5px', borderRadius: '3px', fontWeight: 700, letterSpacing: '1px', background: n.bg, color: n.color }}>{n.badge}</span>
        </div>
      ))}
      <p style={{ fontSize: '10px', color: 'var(--ink-muted)', marginTop: '8px' }}>Click any file to open the diff →</p>
    </div>
  );

  // tabs
  return (
    <div style={{ ...s, flexDirection: 'column', padding: '16px' }}>
      <div style={{ background: 'rgba(6,18,12,.8)', borderRadius: '10px', border: '1px solid var(--line)', width: '100%' }}>
        <div style={{ display: 'flex', borderBottom: '1px solid var(--line)', padding: '0 14px' }}>
          {['my-project', 'api-server', 'frontend'].map((t, i) => (
            <div key={t} style={{ padding: '9px 15px', fontSize: '11px', borderRadius: '8px 8px 0 0', border: '1px solid transparent', borderBottom: 'none', cursor: 'pointer', marginBottom: '-1px', background: i === 0 ? 'var(--bg-2, #0a1a12)' : 'transparent', borderColor: i === 0 ? 'var(--line)' : 'transparent', color: i === 0 ? 'var(--sage)' : 'var(--ink-muted)' }}>{t}</div>
          ))}
          <div style={{ marginLeft: 'auto', padding: '9px 12px', fontSize: '15px', color: 'var(--ink-muted)', cursor: 'pointer' }}>+</div>
        </div>
        <div style={{ padding: '20px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', padding: '5px 13px', borderRadius: '20px', background: '#b6d4a7', fontSize: '11px', fontWeight: 600, color: '#06120c' }}>⬡ my-project</div>
        </div>
      </div>
    </div>
  );
}

export function TourWizard() {
  const [slide, setSlide] = useState(0);
  const router = useRouter();

  function finish() {
    router.push('/download');
    router.refresh();
  }

  const current = SLIDES[slide];

  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '290px 1fr', gap: '0',
      width: '840px', height: '510px', borderRadius: 'var(--ar)',
      overflow: 'hidden', border: '1px solid var(--line-2)',
      boxShadow: 'var(--shadow)', position: 'relative',
    }}>
      {/* Top edge glow */}
      <div style={{ position: 'absolute', top: 0, left: '10%', right: '10%', height: '1px', background: 'linear-gradient(90deg, transparent, var(--sage-glow), transparent)', zIndex: 5 }} />

      {/* Sidebar */}
      <div style={{ background: 'rgba(6,12,9,.98)', borderRight: '1px solid var(--line)', padding: '30px 26px', display: 'flex', flexDirection: 'column' }}>
        <div className="arb-logo" style={{ marginBottom: '26px' }}>arbo<strong>viz</strong></div>

        <div style={{ flex: 1 }}>
          {SLIDES.map((s, i) => (
            <div
              key={i}
              onClick={() => setSlide(i)}
              style={{
                display: 'flex', alignItems: 'flex-start', gap: '11px',
                padding: '8px 0', cursor: 'pointer',
                opacity: i === slide ? 1 : i < slide ? .55 : .35,
                transition: 'opacity .3s',
              }}
            >
              <div style={{
                width: '22px', height: '22px', borderRadius: '50%', flexShrink: 0,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '9px', fontWeight: 600,
                background: i === slide ? 'var(--sage)' : i < slide ? 'rgba(182,212,167,.15)' : 'transparent',
                border: i === slide ? '1px solid var(--sage)' : i < slide ? '1px solid var(--sage)' : '1px solid var(--line)',
                color: i === slide ? '#06120c' : i < slide ? 'var(--sage)' : 'var(--ink-muted)',
              }}>{i + 1}</div>
              <div>
                <div style={{ fontSize: '11px', color: 'var(--ink)', marginBottom: '2px' }}>{s.title.split(',')[0].split('.')[0]}</div>
                <div style={{ fontSize: '9px', color: 'var(--ink-muted)', lineHeight: 1.4 }}>{s.tag.split('— ')[1]}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
          <button
            onClick={() => setSlide(Math.max(0, slide - 1))}
            disabled={slide === 0}
            style={{ flex: 1, padding: '8px', borderRadius: '8px', background: 'transparent', border: '1px solid var(--line)', color: 'var(--ink-muted)', fontFamily: "'Geist Mono', monospace", fontSize: '10px', cursor: 'pointer', opacity: slide === 0 ? .3 : 1 }}
          >← Prev</button>
          {slide < SLIDES.length - 1 ? (
            <button onClick={() => setSlide(slide + 1)} style={{ flex: 1, padding: '8px', borderRadius: '8px', background: 'var(--sage)', border: 'none', color: '#06120c', fontFamily: "'Geist Mono', monospace", fontSize: '10px', fontWeight: 600, cursor: 'pointer' }}>Next →</button>
          ) : (
            <button onClick={finish} style={{ flex: 1, padding: '8px', borderRadius: '8px', background: 'var(--sage)', border: 'none', color: '#06120c', fontFamily: "'Geist Mono', monospace", fontSize: '10px', fontWeight: 600, cursor: 'pointer' }}>Get started ✓</button>
          )}
        </div>
      </div>

      {/* Main */}
      <div style={{ padding: '34px', display: 'flex', flexDirection: 'column', background: 'rgba(10,20,15,.6)' }}>
        <div style={{ fontSize: '9px', letterSpacing: '3px', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: '10px' }}>{current.tag}</div>
        <h2 style={{ fontFamily: "'Fraunces', serif", fontWeight: 300, fontStyle: 'italic', fontSize: '24px', color: 'var(--ink)', marginBottom: '7px' }}>{current.title}</h2>
        <p style={{ fontSize: '11px', color: 'var(--ink-muted)', lineHeight: 1.75, marginBottom: '18px', maxWidth: '360px' }}>{current.desc}</p>
        <SlideVisual type={current.visual} />

        {/* Skip */}
        <button onClick={finish} style={{ marginTop: '12px', background: 'none', border: 'none', color: 'var(--ink-muted)', fontSize: '10px', cursor: 'pointer', fontFamily: "'Geist Mono', monospace', letterSpacing: '1px' }}>
          Skip tour → go to install
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Create tour page**

```tsx
// app/onboarding/tour/page.tsx
import { TourWizard } from '@/components/tour-wizard';

export default function TourPage() {
  return (
    <main style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', position: 'relative', zIndex: 1,
    }}>
      <TourWizard />
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add components/tour-wizard.tsx app/onboarding/tour/page.tsx
git commit -m "feat: 8-slide product tour wizard with sidebar nav"
```

---

## Task 11: CopyCommand + Download page

**Files:**
- Create: `components/copy-command.tsx`
- Create: `app/download/page.tsx`

- [ ] **Step 1: Create CopyCommand component**

```tsx
// components/copy-command.tsx
'use client';

import { useState } from 'react';

export function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(command);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  return (
    <div style={{
      fontFamily: "'Geist Mono', monospace", fontSize: '12px',
      color: 'var(--sage)', background: 'rgba(182,212,167,.06)',
      padding: '10px 12px', borderRadius: '8px', border: '1px solid var(--line)',
      position: 'relative', marginBottom: '10px',
    }}>
      {command}
      <button
        onClick={copy}
        style={{
          position: 'absolute', right: '8px', top: '50%', transform: 'translateY(-50%)',
          fontSize: '10px', color: copied ? 'var(--sage)' : 'var(--ink-muted)',
          padding: '2px 6px', borderRadius: '4px', background: 'var(--bg)',
          border: `1px solid ${copied ? 'var(--sage)' : 'var(--line)'}`,
          cursor: 'pointer', transition: 'all .2s',
          fontFamily: "'Geist Mono', monospace",
        }}
      >
        {copied ? 'copied!' : 'copy'}
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create download page**

```tsx
// app/download/page.tsx
import { currentUser } from '@clerk/nextjs/server';
import { CopyCommand } from '@/components/copy-command';

export default async function DownloadPage() {
  const user = await currentUser();
  const name = (user?.publicMetadata?.display_name as string) || user?.firstName || 'there';

  const steps = [
    {
      num: 'Step 01 — Install',
      cmd: 'pip install arboviz',
      desc: 'Requires Python 3.11+. Installs the CLI globally on your system.',
    },
    {
      num: 'Step 02 — Open a project',
      cmd: 'arboviz ~/my-project',
      desc: 'Point it at any folder. It opens in your browser in under a second.',
    },
    {
      num: 'Step 03 — Explore',
      cmd: 'http://localhost:9215',
      desc: 'Your project opens as an interactive canvas. That\'s it.',
    },
  ];

  return (
    <main style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      minHeight: '100vh', position: 'relative', zIndex: 1, padding: '40px',
    }}>
      <div style={{ maxWidth: '680px', width: '100%', textAlign: 'center' }}>

        <h1 style={{
          fontFamily: "'Fraunces', serif", fontWeight: 300, fontStyle: 'italic',
          fontSize: '44px', color: 'var(--ink)', marginBottom: '8px', lineHeight: 1.1,
        }}>
          You're in,{' '}
          <em style={{ fontStyle: 'normal', color: 'var(--sage)' }}>{name}.</em>
        </h1>
        <p style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '44px' }}>
          Arboviz is ready. Get it running in under a minute.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '14px', marginBottom: '36px' }}>
          {steps.map(step => (
            <div
              key={step.num}
              style={{
                background: 'var(--pop-bg)', border: '1px solid var(--line)',
                borderRadius: '20px', padding: '22px 18px', textAlign: 'left',
              }}
            >
              <div style={{ fontSize: '9px', letterSpacing: '2px', textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: '12px' }}>
                {step.num}
              </div>
              <CopyCommand command={step.cmd} />
              <p style={{ fontSize: '11px', color: 'var(--ink-muted)', lineHeight: 1.6 }}>{step.desc}</p>
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: '12px', justifyContent: 'center' }}>
          {['Documentation', 'GitHub', 'Discord'].map(link => (
            <a
              key={link}
              href="#"
              style={{
                fontSize: '11px', color: 'var(--ink-muted)', textDecoration: 'none',
                padding: '8px 18px', border: '1px solid var(--line)', borderRadius: '8px',
                transition: 'all .2s',
              }}
            >
              {link}
            </a>
          ))}
        </div>
      </div>
    </main>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add components/copy-command.tsx app/download/page.tsx
git commit -m "feat: download page with personalised greeting and install steps"
```

---

## Task 12: Root redirect page

**Files:**
- Modify: `app/page.tsx`

- [ ] **Step 1: Replace app/page.tsx with smart redirect**

```tsx
// app/page.tsx
import { auth } from '@clerk/nextjs/server';
import { redirect } from 'next/navigation';

export default async function RootPage() {
  const { userId, sessionClaims } = await auth();
  if (!userId) redirect('/sign-up');

  const pub = (sessionClaims?.publicMetadata ?? {}) as {
    access_granted?: boolean;
    onboarded?: boolean;
  };

  if (!pub.access_granted) redirect('/invite');
  if (!pub.onboarded) redirect('/onboarding');
  redirect('/download');
}
```

- [ ] **Step 2: Commit**

```bash
git add app/page.tsx
git commit -m "feat: root page smart redirect based on auth state"
```

---

## Task 13: Clerk account setup + local end-to-end test

**Files:**
- Modify: `.env.local` (fill in real keys)

- [ ] **Step 1: Create Clerk app**

1. Go to https://dashboard.clerk.com
2. Create new application named "Arboviz"
3. Enable: **Email/password** + **GitHub OAuth**
4. Copy publishable key and secret key

- [ ] **Step 2: Fill in .env.local**

```bash
# Replace values in .env.local:
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_<your-real-key>
CLERK_SECRET_KEY=sk_test_<your-real-key>
```

- [ ] **Step 3: Start dev server**

```bash
npm run dev
```

- [ ] **Step 4: Walk the full flow manually**

Open http://localhost:3000 and verify each step:

1. `/` → redirects to `/sign-up` ✓
2. Sign up with email → redirects to `/invite` ✓
3. Enter `ARB-ALPHA` → redirects to `/onboarding` ✓
4. Enter name → step 2 ✓
5. Select use case + submit → redirects to `/onboarding/tour` ✓
6. Walk tour + finish → redirects to `/download` ✓
7. `/download` shows personalised greeting with correct name ✓
8. Revisit `/invite` → redirects to `/download` ✓
9. Revisit `/onboarding` → redirects to `/download` ✓
10. Sign in as same user → goes straight to `/download` ✓

---

## Task 14: Deploy to Vercel

- [ ] **Step 1: Install Vercel CLI if needed**

```bash
npm install -g vercel
vercel whoami
```

Expected: shows `friday@infinivoai.eu` and team `friday-6083s-projects`.
If wrong account: `vercel logout && vercel login`.

- [ ] **Step 2: Deploy**

```bash
cd "/Users/smb/Infinivo AI Workspace/personal projects/arboviz-web"
vercel --prod
```

When prompted:
- Link to existing project? **No**
- Project name: **arboviz-web**
- Directory: **./`** (current)
- Override settings? **No**

- [ ] **Step 3: Set environment variables on Vercel**

```bash
vercel env add NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY production
# paste key when prompted

vercel env add CLERK_SECRET_KEY production
# paste key when prompted

vercel env add NEXT_PUBLIC_CLERK_SIGN_IN_URL production
# value: /sign-in

vercel env add NEXT_PUBLIC_CLERK_SIGN_UP_URL production
# value: /sign-up

vercel env add NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL production
# value: /

vercel env add NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL production
# value: /invite

vercel env add INVITE_CODES production
# value: ARB-ALPHA,ARB-BETA01,ARB-DEMO01
```

- [ ] **Step 4: Redeploy with env vars**

```bash
vercel --prod
```

- [ ] **Step 5: Add production URL to Clerk allowed origins**

In Clerk dashboard → Domains → add the Vercel production URL.

- [ ] **Step 6: Smoke test production URL**

Visit the Vercel URL and walk through the full flow from sign-up to download page.

- [ ] **Step 7: Final commit**

```bash
git add -A
git commit -m "chore: arboviz-web complete — auth, onboarding, tour, download"
```

---

## Self-Review

**Spec coverage:**
- ✅ Next.js 15 App Router
- ✅ Clerk auth (sign-in, sign-up)
- ✅ Middleware with full pipeline redirect logic
- ✅ Invite code gate (server action, env var codes)
- ✅ Onboarding step 1 (name) + step 2 (use case)
- ✅ 8-slide product tour with sidebar
- ✅ Download page with personalised greeting + install steps
- ✅ Root redirect page
- ✅ Arboviz design system (28px Apple corners, CSS tokens, fonts)
- ✅ ArbovizTree SVG with correct bezier geometry
- ✅ Vercel deploy with env var setup

**Type consistency check:**
- `access_granted`, `onboarded`, `display_name`, `use_case` — consistent across middleware, validate-invite, complete-onboarding, and download page ✅
- `completeOnboarding` takes `FormData` and returns `{ success, error? }` — matches usage in onboarding page ✅
- `validateInvite` same signature — matches invite page usage ✅
- `clerkAppearance` exported from `lib/clerk-appearance.ts` — imported in sign-in and sign-up ✅
