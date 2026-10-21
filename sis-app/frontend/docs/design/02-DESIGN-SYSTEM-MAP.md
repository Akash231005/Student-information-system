# 02 — SIS Retro Desktop Design System

## Product interpretation

The reference is a desktop theme by niivu, not a ready-made web UI kit. The SIS should borrow its art direction while retaining web-app accessibility and academic workflow clarity.

## Design laws

1. **Canvas owns the wallpaper.** Use one recognizable pastel geometric background on the outer application canvas. Keep it low-frequency and low-contrast behind content.
2. **Content lives in windows.** Major application regions use framed, opaque surfaces. Each window has a clear boundary and a purposeful title/header region.
3. **One chrome grammar.** Use the same corner radii, outline colors, control sizes, and title-bar rhythm across sidebar, topbar, cards, dialogs, and panels.
4. **Depth comes from framing, not blur.** Use thin dark outlines and restrained, offset shadows. Do not combine heavy shadow, glass refraction, gradients, and thick outlines on the same component.
5. **Pastels are structural.** Cream is the main surface, mint is the primary highlight, blush/lilac are secondary categories, and charcoal anchors contrast. Bright lime is reserved for primary actions or success states.
6. **Typography has roles.** Use a friendly modern sans for headings/body, a compact mono for metadata, IDs, timestamps and technical labels. Do not use monospace for long body copy.
7. **Icons must be a system.** Keep one stroke weight, optical size, and alignment. Use Lucide for functional icons; avoid mixing random emoji, pixel art and outline icons.
8. **Windows are not fake controls.** Title-bar dots are decorative unless they perform a real action. Every interactive element must be a real button/link with a focus state.
9. **Light and dark are siblings.** Preserve spacing, component geometry and semantic color roles across themes. Dark mode changes surfaces and wallpaper contrast, not the whole layout.
10. **Data gets a quiet reading zone.** Tables, forms, grade details and API output use solid, high-contrast surfaces with clear row separation. The wallpaper never competes with data.
11. **Use asymmetry sparingly.** Overlapping windows and varied card sizes are useful for the overview and hero. Forms and tables use predictable alignment.
12. **Responsive design is a first-class layout.** Desktop can feel like a desktop environment; mobile becomes a single-column workspace, not a miniature desktop screenshot.

## Tokens (initial implementation values)

| Token | Value | Purpose |
|---|---|---|
| Canvas | `#F4EEDF` | warm desktop background |
| Window | `#FFF9EB` | opaque content surfaces |
| Ink | `#292B26` | outlines and primary text |
| Muted ink | `#66685E` | secondary labels |
| Mint | `#B9E2D9` | primary brand field/highlight |
| Deep mint | `#4D9287` | accessible accent for links/status |
| Blush | `#E9C9BD` | secondary accent |
| Lilac | `#DCD4EA` | secondary category |
| Lime | `#DDF18A` | primary CTA and positive action |
| Dark canvas | `#27312F` | dark-mode desktop field |
| Dark window | `#343D39` | dark-mode panels |
| Dark ink | `#F4F0E4` | dark-mode foreground |

These are implementation tokens inferred from the preview, not official values from the original theme files.

## Shape and spacing rules

- Outer frame: 14–20px radius, 2px outline, inset highlight only where it supports the frame.
- Window/panel: 8–12px radius, 1.5–2px outline.
- Small controls: 4–6px radius, clear 1.5px outline.
- Hard shadow: 3–5px offset, no large blur; use only on primary windows and elevated actions.
- Title strip: 34–42px tall on desktop, with compact metadata and controls.
- Layout rhythm: 8px base spacing; 16px component gap; 24–32px page padding.
- Desktop wallpaper: broad pastel geometry, no high-frequency texture that interferes with text.

## SIS-specific constraints

- Overview may use the most expressive wallpaper, hero and asymmetric panel composition.
- Course catalogue may use accent tabs and framed course cards but must preserve search, capacity, status and action visibility.
- Enrollment, grades and attendance should prioritize form labels, validation, tables and explicit states.
- Faculty operations can use an application-window metaphor with a clear title strip and grouped tasks.
- System observability can look like a technical utility window; JSON and metrics need dark/high-contrast code surfaces.
- Do not use fake desktop shortcuts as the only way to navigate core SIS functions.
