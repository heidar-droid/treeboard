# Arboviz — Auth, Onboarding & Download Flow
**Date**: 2026-05-19  
**Stack**: Next.js 15 (App Router) · Clerk · Tailwind CSS · Vercel  
**Design ref**: `docs/superpowers/specs/arboviz-brand-design-spec.md`

---

## Overview

A standalone Next.js web app that handles Arboviz's auth, invite-gate, onboarding wizard, product tour, and post-install download page. Deployed to Vercel. Uses Clerk for auth — no custom auth logic. Access is invite-only: users must enter a valid invite code after signup before reaching onboarding.

---

## Architecture

```
arboviz-web/                  ← new Next.js app (separate from Python CLI repo)
├── app/
│   ├── layout.tsx            ← ClerkProvider, fonts, global CSS
│   ├── page.tsx              ← redirect: signed-in → /download, else → /sign-in
│   ├── sign-in/[[...sign-in]]/page.tsx
│   ├── sign-up/[[...sign-up]]/page.tsx
│   ├── invite/page.tsx       ← invite code gate
│   ├── onboarding/
│   │   ├── page.tsx          ← step 1: name, step 2: use case
│   │   └── tour/page.tsx     ← 8-slide product tour wizard
│   └── download/page.tsx     ← install page (protected)
├── middleware.ts             ← Clerk auth + redirect logic
├── actions/
│   ├── validate-invite.ts    ← server action: check code, set publicMetadata
│   └── complete-onboarding.ts ← server action: save name/usecase, set onboarded
└── components/
    ├── arboviz-tree.tsx      ← animated SVG canvas preview (from mockup)
    ├── tour-wizard.tsx       ← 8-slide product tour with sidebar
    └── code-block.tsx        ← copy-to-clipboard command block
```

---

## Routes & Access Rules

| Route | Auth required | Access condition | Redirect if fails |
|---|---|---|---|
| `/sign-in` | No | — | — |
| `/sign-up` | No | — | — |
| `/invite` | Yes | `!publicMetadata.access_granted` | `/download` if already granted |
| `/onboarding` | Yes | `access_granted && !onboarded` | `/download` if already onboarded |
| `/onboarding/tour` | Yes | `access_granted && !onboarded` | — |
| `/download` | Yes | `access_granted && onboarded` | `/onboarding` if not onboarded |

---

## Middleware Logic

```typescript
// middleware.ts
export default clerkMiddleware(async (auth, req) => {
  const { userId, sessionClaims } = await auth();
  const path = req.nextUrl.pathname;
  const pub = (sessionClaims?.publicMetadata ?? {}) as Record<string, boolean>;

  // Public routes — let through
  if (['/sign-in', '/sign-up'].some(p => path.startsWith(p))) return;

  // Not signed in → sign-in
  if (!userId) return NextResponse.redirect(new URL('/sign-in', req.url));

  // Signed in, no access → invite (unless already on /invite)
  if (!pub.access_granted && !path.startsWith('/invite'))
    return NextResponse.redirect(new URL('/invite', req.url));

  // Has access, not onboarded → onboarding (unless already there)
  if (pub.access_granted && !pub.onboarded && !path.startsWith('/onboarding'))
    return NextResponse.redirect(new URL('/onboarding', req.url));

  // Fully onboarded, trying to revisit /invite or /onboarding → /download
  if (pub.onboarded && (path.startsWith('/invite') || path.startsWith('/onboarding')))
    return NextResponse.redirect(new URL('/download', req.url));
});
```

---

## Invite Code System

- Invite codes stored as a comma-separated env var: `INVITE_CODES=ARB-ALPHA,ARB-BETA01,ARB-XXXXX`
- Server action `validate-invite.ts` checks submitted code against the list
- On success: calls `clerkClient.users.updateUserMetadata(userId, { publicMetadata: { access_granted: true } })`
- On failure: returns `{ error: "Invalid code" }` — client shows inline error, no reload
- Codes are case-insensitive, trimmed

---

## Onboarding Flow

### Step 1 — Name (`/onboarding?step=1`)
- Single input: preferred name
- Saved to `user.firstName` via Clerk + `publicMetadata.display_name`
- Progress indicator: 2 dots, first active

### Step 2 — Use Case (`/onboarding?step=2`)
- Three options: Solo developer / Team / Open source
- Saved to `publicMetadata.use_case`
- On submit: server action sets `publicMetadata.onboarded = true`
- Redirect to `/onboarding/tour`

### Product Tour (`/onboarding/tour`)
- 8 slides with left sidebar navigation (as designed in mockup)
- Sidebar shows all 8 steps; active one highlighted in sage green
- Each slide: tag + Fraunces title + muted description + visual
- Slides: Canvas · Navigate · Open Files · Resize · Pin Bar · Control Center · Git Mode · Project Tabs
- "Finish Tour" button on last slide → `/download`
- Tour completion NOT required — skip button always available → `/download`

---

## Download Page (`/download`)

- Personalised: "You're in, {displayName}." (Fraunces italic, sage green name)
- Three-step install cards:
  1. `pip install arboviz` (with copy button)
  2. `arboviz ~/my-project` (with copy button)
  3. `http://localhost:9215` (auto-opens on install)
- Footer links: Documentation · GitHub · Discord
- No re-onboarding prompt — once onboarded, this is home

---

## Design Implementation

Follow `arboviz-brand-design-spec.md` exactly:

- **Fonts**: Fraunces (display) + Geist Mono (body) — loaded via `next/font/google`
- **Colors**: exact CSS custom properties from spec
- **Cards**: `border-radius: 28px` (--apple-radius), `background: rgba(8,14,11,.96)`, top-edge glow pseudo
- **Buttons**: primary = sage fill, ghost = transparent + line border; both `border-radius: 10px`
- **Inputs**: `border-radius: 10px`, sage focus ring
- **Background**: dark `#06120c` + dot grid + radial glow — applied at layout level
- **ArbovizTree component**: exact SVG from mockup — bezier edges, correct pill dimensions, animated entry
- **No Tailwind defaults for colors** — CSS custom properties only; Tailwind used for layout/spacing only

---

## Clerk Appearance Config

```typescript
const appearance = {
  variables: {
    colorPrimary: '#b6d4a7',
    colorBackground: 'rgba(8,14,11,.96)',
    colorInputBackground: 'rgba(182,212,167,.05)',
    colorText: '#b6d4a7',
    colorTextSecondary: '#7c8c75',
    borderRadius: '10px',
    fontFamily: '"Geist Mono", ui-monospace, monospace',
  },
  elements: {
    card: 'arboviz-clerk-card',
    formButtonPrimary: 'arboviz-btn-primary',
  }
};
```

Note: we use **custom sign-in/sign-up pages** (not Clerk-hosted), embedding Clerk's `<SignIn>` and `<SignUp>` components with the appearance config above.

---

## Environment Variables (Vercel)

```
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...
NEXT_PUBLIC_CLERK_SIGN_IN_URL=/sign-in
NEXT_PUBLIC_CLERK_SIGN_UP_URL=/sign-up
NEXT_PUBLIC_CLERK_AFTER_SIGN_IN_URL=/
NEXT_PUBLIC_CLERK_AFTER_SIGN_UP_URL=/invite
INVITE_CODES=ARB-ALPHA,ARB-BETA01
```

---

## Out of Scope

- Email verification customisation (Clerk handles)
- Billing / subscription
- Team / org features
- Any backend beyond Clerk metadata
- Database (no Supabase/Postgres needed — all state in Clerk publicMetadata)
