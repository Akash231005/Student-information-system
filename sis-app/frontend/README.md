# Orbit SIS frontend

React 19 + TypeScript + Vite frontend for the Student Information System. FastAPI and PostgreSQL remain the API/data layer; the frontend is a separate SPA build served by FastAPI from `dist/` in normal use.

## Start development

From this directory:

```bash
npm ci
npm run dev
```

Open http://127.0.0.1:5173/. The Vite development frontend calls FastAPI at `http://127.0.0.1:8000`; start the backend separately from `../` with `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.

## Build and serve

```bash
npm ci
npm run build
```

The compiled app is written to `dist/`. FastAPI serves it at http://127.0.0.1:8000/ when `dist/` exists. If no build exists yet, FastAPI temporarily falls back to the legacy HTML page.

## UI system and source references

- **Motion for React** handles page transitions and transient toast messages.
- **Lucide React** provides consistent line icons.
- **Tailwind CSS v4** is configured for source-based component installs; the dashboard styling itself is expressed in a small set of readable CSS tokens and component classes.
- `src/components/ui/` holds the shadcn/ui scaffold produced during exploration; the dashboard components are hand-written.
- `macindows.css` is a superseded earlier theme layer and is no longer imported.

Public references: https://ui.shadcn.com/docs/installation/vite · https://motion.dev · https://lucide.dev

### Visual direction

**Peak 80s/90s graphic poster.** Off-white paper (`#f4efe3`) with a fixed halftone dot field, ink-black
(`#1c1a18`) 3px borders, square corners, and hard non-blurred offset shadows (`5px 5px 0`). Accents are a
poster palette of coral `#ff5a4f`, electric blue `#2d5bff`, mustard `#f5c542`, lavender `#b7a4f0`, violet
`#7a62e8` and mint `#2fb8a0`. Type is Bungee for display, Space Grotesk for body and VT323 for mono
labels.

Styling is layered, not rewritten: `index.css` → `App.css` (base layout and components) →
`src/retro.css` (the retro theme layer, imported last from `App.tsx`). Read `retro.css` as the single
source of truth for the current look; it also carries the dark-theme token block and the contrast and
legibility overrides.

The earlier "glass"/editorial direction was dropped deliberately: a student information system benefits
more from crisp hierarchy, readable forms and visible data than from blur layered across every panel.
Contrast and type size are treated as correctness: every text pair is explicitly set for both themes and
nothing renders below 12 px.

## Notes

- Auth tokens are held in `sessionStorage` for the current browser session.
- Vite's development server uses port 5173 and the API uses port 8000; FastAPI allows only those two local development origins.
- Build output is generated and is not a replacement for the source under `src/`.

## Macindows-inspired visual system

The current visual direction is inspired by the visible art direction of [Macindows for Windows 10 by niivu](https://www.deviantart.com/niivu/art/Macindows-for-Windows-10-870073866): pastel geometric wallpaper, framed desktop canvas, cream application surfaces, compact window-like chrome, coordinated icons, and sibling light/dark palettes. It is an original web adaptation, not a copy of the Windows theme files. The VSThemes listing was unavailable to fetch during implementation, so exact bundled assets and official color/font tokens remain unverified.

Design documentation lives in `docs/design/`:

- `01-MACINDOWS-REFERENCE-MAP.md`: visual evidence, reference links and confidence boundaries.
- `02-DESIGN-SYSTEM-MAP.md`: design laws, inferred tokens, geometry, typography and SIS-specific constraints.
- `03-IMPLEMENTATION-MAP.md`: current component mapping, implementation sequence and quality gates.

The custom geometric desktop wallpaper is `public/macindows-wallpaper.svg`. The active reference layer is `src/macindows.css`; it is imported after `src/App.css`. Liquid Glass wrappers were removed from the application shell and replaced with native semantic surfaces and controls. Motion remains for page transitions and notifications.
