# SIS Frontend Design System — Editorial Campus Workspace

## Design thesis

Build a high-trust academic workspace with an editorial, product-led look rather than a generic dark glass dashboard. The signature is a warm near-white canvas, deep ink typography, cobalt blue, mint signals, restrained lavender and amber categories, crisp cards, and a custom geometric campus illustration. Academic forms and records prioritize readability and directness over decorative blur.

## Research references reviewed (19 October 2026)

- Apple Human Interface Guidelines — Materials: https://developer.apple.com/design/human-interface-guidelines/materials
- Apple — Liquid Glass overview: https://developer.apple.com/documentation/TechnologyOverviews/liquid-glass
- Apple — Adopting Liquid Glass: https://developer.apple.com/documentation/TechnologyOverviews/adopting-liquid-glass
- React Bits — component catalog: https://reactbits.dev/
- React Bits — animated backgrounds: https://www.reactbits.dev/c/backgrounds
- React Bits — grid distortion component: https://reactbits.dev/backgrounds/grid-distortion
- Cult UI — open-source shadcn component registry: https://www.cult-ui.com/
- Cult UI — installation: https://www.cult-ui.com/docs/installation
- Cult UI — theming: https://www.cult-ui.com/docs/theming
- Aceternity UI — component catalog: https://ui.aceternity.com/components
- Aceternity UI — backgrounds: https://ui.aceternity.com/background
- Magic UI — component catalog: https://magicui.design/docs/components
- 21st.dev — React components and templates: https://docs.21st.dev/
- shadcn/ui — design-system foundation: https://ui.shadcn.com/docs
- MDN — prefers-reduced-motion: https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/%40media
- Tailwind CSS — backdrop-filter concepts: https://tailwindcss.com/docs/backdrop-filter

## Curated component sources and placement (19 October 2026)

The project uses a small set of source-owned components instead of mixing unrelated UI kits. Candidate libraries were evaluated by fit, accessibility, styling ownership, and whether their effects make sense for a form-heavy academic application.

| Source | Best-fit components / strengths | Decision and placement |
|---|---|---|
| [OpenGlass UI](https://github.com/moekoelueker/open-glass-ui) | `Glass`, `Button`, `SegmentedControl`, `Badge`, `Tabs`, `Tooltip`, `Drawer`, `Dialog`, `Toast`, `SearchField` | **Selected and installed.** Use its actual liquid-glass primitives for the persistent sidebar/topbar and key controls. The hero CTA and account-mode segmented control now use its real components. |
| [shadcn/ui](https://ui.shadcn.com/) | Source-owned forms, dialogs, menus, tables, dropdowns, and primitives | Keep as the underlying source-owned component foundation where a functional primitive is needed; avoid replacing working application workflows just for visual uniformity. |
| [Liquid Glass React — aberhamm](https://github.com/aberhamm/liquid-glass-react) | `LiquidGlass`, `GlassButton`, `GlassCard`, `GlassSegmentedControl`; explicit browser fallbacks | **Evaluated, not installed.** Alternative if OpenGlass cannot deliver a required glass control; do not run two glass engines side-by-side. |
| [React Bits](https://github.com/DavidHDev/react-bits) | Creative motion, backgrounds, text treatments, microinteractions | **Reference catalogue only in this iteration.** Could supply one restrained hero/empty-state animation, but not table rows, form controls, or every card. Its current repository uses MIT + Commons Clause, so check exact component terms before redistributing. |
| [Aceternity UI](https://ui.aceternity.com/components) | Spotlight, hover cards, grid and background effects, hero blocks | Use selectively for a hero or system-observability showcase; avoid importing a landing-page effect into routine admin flows. |
| [Cult UI](https://github.com/nolly-studio/cult-ui) | Animated buttons and shadcn-compatible source components | The previous HaloButton treatment was removed from the hero because it introduced a second button visual language beside the glass controls. Reconsider only for a specific, justified interaction. |
| [Magic UI](https://magicui.design/docs/components) | Animated visual primitives and decorative UI | Candidate for a small decorative accent, not core forms, course records, or navigation. |
| [21st.dev](https://docs.21st.dev/) | Community React component discovery and copyable patterns | Useful for finding alternatives, but each component must be inspected for source, accessibility, dependencies, and license before adoption. |
| [Liquid Glass for the Web](https://liquidglass.dev/) and [samasante/liquid-glass](https://github.com/samasante/liquid-glass) | Experimental refractive lens techniques and live DOM effects | Research references only. Real refraction has browser-specific limits and should be restricted to small surfaces, not the whole dashboard. |

### Placement rules

- **Sidebar and topbar:** liquid glass, because they are persistent navigation/control chrome and sit above the content.
- **Primary hero action and account mode switch:** real OpenGlass `Button` and `SegmentedControl` components, not hand-built imitations.
- **Course tables, offerings, forms, profile fields and API output:** opaque, high-contrast surfaces for scanning and input accuracy.
- **Status indicators:** use restrained semantic badges/chips; color communicates state, not decoration.
- **Hero illustration:** one expressive visual field; remove pointer-magnet behavior from routine controls.
- **Dialogs, drawers, menus and tooltips:** prefer accessible primitives from the selected source-owned component system instead of custom overlays.
- **Experimental refraction:** never apply to large surfaces by default; compare browser fallbacks and performance before enabling it.

### Community feedback considered

A September 2026 Reddit discussion of Plasma UI reported desktop-performance issues in Firefox/Safari and jitter on Android Chrome, despite improvements noted by the author. This is anecdotal rather than a benchmark, but it reinforces the choice not to put canvas/WebGL-style liquid effects across the whole dashboard: https://www.reddit.com/r/reactjs/comments/1wj276e/plasma_ui_liquid_panels_for_react_that_fuse_on/ . A separate UI-design discussion on glassmorphism emphasized spacing as a key factor in polished compact dashboard widgets: https://www.reddit.com/r/UI_Design/comments/1p1ecfj/how_are_people_making_these_tiny_glassmorphism/ .

## Visual tokens

- Background: `#f5f6fa` warm cool-neutral canvas, white panels, deep ink text.
- Primary accent: cobalt `#4f65f6`; mint `#5ed6ac`; secondary lavender `#8f7bf2` and amber `#ffb568`.
- Typography: Manrope for headings, DM Sans for UI copy, DM Mono for technical identifiers.
- Surfaces: crisp white cards, light 1px borders, restrained shadows; glass is reserved for small floating labels, not the overall page.
- Geometry: 9–19px radii, compact controls, consistent spacing rhythm, strong type hierarchy.
- Motion: Motion for React page transitions and toasts; keep hover feedback restrained and honor reduced-motion preferences.

## Component map

- Navigation rail / mobile slide-in drawer: persistent wayfinding and active section state.
- Hero: one strong message, two actions, custom orbital SVG illustration, ambient grid.
- Summary tiles: live catalogue, offering, seat-availability and registration counts.
- Course search: query field, explicit search action, separate offering list, live API output.
- Account: registration, sign-in, profile update, security reminder.
- Enrollment: student/offering IDs, clear call to action, database invariant explanation.
- Academic records: grades, timetable, notifications.
- Staff operations: course and offering setup, attendance, assessment, grade entry, timetable, notifications.
- System playground: metrics, ring, route, autocomplete, short link, ID generation.
- Feedback wells: API responses are announced through `aria-live` and remain readable at small sizes.

## Architecture decision

The frontend is a React 19 + TypeScript + Vite SPA under `sis-app/frontend`. FastAPI remains the API/data layer and serves the compiled `frontend/dist` assets for the production local experience. Vite runs on port 5173 during development and calls FastAPI on port 8000; FastAPI permits only those local dev origins. shadcn/ui provides editable, source-owned primitives. OpenGlass UI provides the selected Liquid Glass layer: its actual `Glass` components render the sidebar and top chrome; its `Button` is used for the hero CTA and its `SegmentedControl` for the sign-in/register mode. The former Cult UI HaloButton and React Bits Magnet wrappers were removed from the hero to avoid conflicting interaction styles. Motion for React drives view transitions, and Lucide React supplies consistent icons. The legacy `web/index.html` is retained only as a fallback if a fresh checkout has not built the React bundle.

## Accessibility and performance guardrails

1. Maintain visible keyboard focus and semantic labels.
2. Respect reduced-motion and reduced-transparency preferences.
3. Keep controls and API output contrast high; glass is not the default surface for every panel.
4. Avoid WebGL/canvas effects on a form-heavy internal app unless profiling demonstrates a benefit.
5. Avoid inventing academic metrics. The overview cards use live course, offering and seat counts returned by the API.
6. Treat remote Google Fonts as progressive enhancement; fallback font stacks remain defined.
7. Recheck narrow viewports and browser support for backdrop filters; the solid backgrounds remain usable without blur.

## Verification

- TypeScript/Vite production build passes after the refraction and typography changes.
- Chromium Playwright passes at 1440×1000, 390×844 and 320×740: HTTP 200, no JavaScript page errors, and no horizontal overflow.
- Mobile menu opens; account registration mode exposes the student-number field.
- Computed styles confirm fixed sidebar, sticky flex topbar, locally loaded Manrope/Geist fonts, and five SVG filters containing `feDisplacementMap` primitives.
- `npm audit --omit=dev`: 0 vulnerabilities.
- Oxlint: 0 errors, 7 advisory warnings (existing React purity/effect patterns and one source-owned button export warning).
- Backend source was not changed in this UI iteration.

## Curated Liquid Glass revision (19 October 2026)

The first pass had too many custom CSS overrides and component styles fighting each other. The revised pass removes the appended hand-built glass layer and the unrelated animated hero button/magnet wrappers. It keeps the base responsive layout, uses the OpenGlass component library's real button and segmented-control implementations, and narrows the glass treatment to navigation chrome.

- **Actual source components:** `GlassSystemProvider` configures OpenGlass; the library's `Glass` components remain the sidebar/topbar surfaces. `Button` is used for the hero CTA and account submit action; `SegmentedControl` handles login/register selection. These are component implementations from the installed library, not imitations made with CSS.
- **Material hierarchy:** sidebar/topbar use translucent glass; hero is the only expressive, luminous surface; data cards, tables, forms, and API output remain largely opaque. This keeps contrast and reading speed ahead of decoration.
- **Removed:** Cult UI `HaloButton` and React Bits `Magnet` wrappers around the hero CTA and illustration. Their motion/edge effects created a separate visual language and were not essential to the SIS workflow.
- **Research references:** [OpenGlass UI](https://github.com/moekoelueker/open-glass-ui), [Liquid Glass React by aberhamm](https://github.com/aberhamm/liquid-glass-react), [shadcn/ui](https://ui.shadcn.com/), [React Bits](https://github.com/DavidHDev/react-bits), [Aceternity UI](https://ui.aceternity.com/components), [Cult UI](https://github.com/nolly-studio/cult-ui), [Magic UI](https://magicui.design/docs/components), [21st.dev](https://docs.21st.dev/), [Liquid Glass for the Web](https://liquidglass.dev/), and the Reddit community discussions listed above.
- **Accessibility/performance:** preserve DOM text, native form semantics, keyboard focus and reduced-motion/reduced-transparency behavior. Do not claim universal real refraction: browser engines differ, and large glass/filter areas can be costly.
- **Validation:** latest TypeScript/Vite production build passes. Oxlint reports 0 errors and 10 existing advisory warnings; the warnings include unused source component files no longer imported and existing React purity/effect patterns. Desktop/mobile browser verification is pending for this revision.


## Liquid-glass + typography refinement (19 October 2026)

The supplied reference demonstrates a bright pearl-grey canvas, thick optical rims, bevel highlights, restrained spectral edge color, rounded capsule controls, and clear type hierarchy. This iteration moved beyond a CSS blur imitation by adding the MIT-licensed [`@aberhamm/liquid-glass-react`](https://github.com/aberhamm/liquid-glass-react) source implementation. Its `LiquidGlass`, `GlassButton`, `GlassCard`, and `GlassSegmentedControl` components use SVG displacement/refraction where the browser supports it and degrade to frosted glass elsewhere. The previous OpenGlass wrapper renderer was CSS-only; it was replaced for the sidebar/topbar surfaces and key controls.

### Component placement

- Sidebar and topbar: `LiquidGlass` with live displacement, conservative scale, low chromatic aberration, and zero elastic pointer motion. The component's own inline layout defaults are explicitly overridden so fixed sidebar, sticky topbar, and flex layouts remain correct.
- Hero CTA: `GlassButton` with a high-contrast coral lens, bevel highlights, a short press sheen, and displacement. Authentication submit uses a blue glass button.
- Account-mode switch: `GlassSegmentedControl` with a refractive active indicator and native radio semantics.
- Main catalogue/search, campus summary and help panels: source `GlassCard`; refraction is enabled only on a small number of key panels to limit GPU work. Other data cards use the component's raised edge/lift treatment without active displacement.
- Hero: pearl-white glass canvas, soft periwinkle/mint/peach light fields, crisp dark type, a refractive-looking central emblem and floating glass notes. The operational data remains readable.

### Typography system

- **Display:** self-hosted `Manrope Variable` for page titles and hero headings, weight 700–800, tight tracking (around `-0.055em`), and compact line height. The variable font is open-source under the SIL Open Font License.
- **Interface:** self-hosted `Geist Variable` for navigation, body copy, controls, table values and forms. Use real variable weights instead of synthetic bold.
- **Numbers:** Geist/Manrope tabular numerals for KPIs; consistent optical sizing.
- **Scale:** page headings around 34–46px; hero heading 31–43px; card headings around 15px; body 13–14px; input text 13px; labels 11px; overlines 10px with tracking. Small metadata stays secondary, not smaller than necessary.
- Fonts are bundled locally with Fontsource; the old remote Google Fonts import and competing DM Sans/Manrope/Geist definitions were removed from the active font stack.

### Rendering and verification

Chromium screenshot passes completed at 1440×1000, 390×844, and 320×740. Each returned HTTP 200, reported no JavaScript page errors, and showed no horizontal overflow. The mobile navigation opens, and the account registration mode exposes the student-number field. Browser computed styles confirmed the intended Manrope display / Geist UI font roles, fixed sidebar, sticky flex topbar, and generated SVG filters. Real live-backdrop refraction is progressive enhancement: the library documents it for Chromium; Safari and Firefox receive the frosted/beveled fallback. We do not promise identical refraction across browsers.

### Research references

- [Liquid Glass React (MIT)](https://github.com/aberhamm/liquid-glass-react): displacement, cross-browser fallback, button/card/segmented components.
- [OpenGlass UI](https://github.com/moekoelueker/open-glass-ui): accessible CSS-first material system and explicit opt-in renderer policy. [Architecture note](https://github.com/moekoelueker/open-glass-ui/blob/main/docs/ARCHITECTURE.md).
- [Geist](https://geistfont.com/): product-interface typeface and variable family.
- [Manrope source font log](https://github.com/google/fonts/blob/main/ofl/manrope/FONTLOG.txt): open-source variable typeface.
- [Reddit discussion on readability](https://www.reddit.com/r/UI_Design/comments/1pn6jy3/struggling_with_liquid_glass_legibility_looking/) and [contrast feedback](https://www.reddit.com/r/UI_Design/comments/1mh7yin): community commentary emphasizes maintaining legible text and controls when backdrops change.
