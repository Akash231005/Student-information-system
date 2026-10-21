# 03 — Implementation Map

## Current frontend inventory

- `src/App.tsx`: all seven SIS sections, navigation, API calls, forms and interaction state.
- `src/App.css`: component styling. It has accumulated multiple appended overrides; avoid adding another override layer indefinitely.
- `src/index.css`: global Tailwind v4 and Geist/Manrope font setup.
- `public/campus-hero.webp`: campus photo from the previous design direction; the Macindows direction should prefer a generated/local geometric wallpaper over a photographic hero.
- `@aberhamm/liquid-glass-react`: previously used for sidebar, topbar, cards and hero CTA. Its refraction is inconsistent with the new reference and should be removed from the main app shell.

## Component mapping

| Existing component | New role | Required behavior |
|---|---|---|
| `.app-shell` | Framed desktop canvas | wallpaper, perimeter, responsive inset |
| `.sidebar` | Finder-like navigation window | opaque surface, title/brand zone, grouped navigation |
| `.topbar` | Application menu/title strip | compact controls, breadcrumbs, term selector |
| `.welcome-banner` | Featured desktop window | geometric field, editorial heading, functional actions |
| `.stat-card` | Utility widgets | concise metrics with status and label hierarchy |
| `.card` | Content windows | consistent outline, surface, title/header alignment |
| `.search-form` | Finder-style search control | real input, visible focus and submit affordance |
| `.course-table-row` | Data table row | stable column alignment, responsive fallback |
| `.field` | Form control group | explicit label, validation, keyboard focus |
| `.api-result` | Developer utility output | readable monospace, wrapping/scrolling, high contrast |
| `.toast` | System notification | clear success/error role and dismissal |

## Implementation sequence

1. Create this map and the reference/design-system maps before changing UI code.
2. Remove Liquid Glass wrappers/imports so CSS can own the surface model without fighting refraction.
3. Establish design tokens and the wallpaper/frame at the global shell level.
4. Normalize sidebar, topbar and content-window chrome.
5. Rework overview composition first, because it can carry the strongest desktop metaphor.
6. Apply the same window language to course catalogue, enrollment, records, account, faculty and observability.
7. Add a dark palette using the same component geometry and semantic roles.
8. Test mobile navigation, table overflow, keyboard focus, reduced motion and API-backed flows.
9. Run `npm run build`; verify visually in a real browser before calling the redesign complete.

## Quality gates

- No broken API interactions, auth flows, forms or section navigation.
- No false UI controls: every visible action works, or is clearly decorative and non-interactive.
- No wallpaper or shadow that harms text/table contrast.
- No horizontal overflow at 320px viewport width.
- Dark mode must remain readable and not force light surfaces unintentionally.
- Reduced-motion preference is respected.
- Use source-derived design choices; do not claim exact theme tokens when only a screenshot is available.

## Source references

- [Macindows by niivu](https://www.deviantart.com/niivu/art/Macindows-for-Windows-10-870073866)
- [VSThemes listing](https://vsthemes.org/en/themes/windows10/26923-macindows.html)
- [98.css documentation](https://jdan.github.io/98.css/)
- [XP.css repository](https://github.com/botoxparty/XP.css)
