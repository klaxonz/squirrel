# ADR 0004: UI system — tokens, shared/ui, and the extension contract

Status: accepted

The renderer has one UI system, layered top-down:

1. **Design tokens** (`shared/styles/layout.css`, `shared/styles/index.css`,
   `themes/dark.css`). Semantic color tokens in shadcn HSL form
   (`--primary`, `--card`, `--muted-foreground`, …), the spacing scale
   (`--space-*`), radius (`--radius-*`), stacking (`--z-*`), motion
   (`--duration-*` / `--ease-*`), and the typography scale
   (`--app-text-2xs … --app-text-3xl`).
2. **Primitives** (`shared/ui/**`). Headless behavior from reka-ui, pixels
   owned by the design system via `sq-*` classes in `components.css`:
   button + icon-button, input, textarea, select, checkbox, switch,
   float-label, dialog, popover, dropdown-menu, tooltip, tabs, alert,
   badge, skeleton (Skeleton/SkeletonText/Spinner/BounceDots).
3. **App chrome** (`shared/components/**`). Page-level compositions with
   app semantics: AppPageShell, AppSectionNav, AppFilterPanel,
   ConfirmDialog, ToastProvider, AppContextMenu, AppEmptyState, …
4. **Features** (`features/**`). Consume layers 1–3; never re-implement
   them.

## Visual language (2026-10 redesign)

The renderer follows the design philosophy of wxad.design: near-monochrome,
editorial spacing, functional motion, and one implementation per semantic.

- **Palette**: neutral paper. Light is `#FAFAFA` canvas / `#FFFFFF` surface /
  `#171717` ink / `#E5E5E5` hairline; dark is graphite (`#0F0F0F` / `#1A1A1A` /
  `#E8E8E8` / `#292929`). `--primary` is ink in both themes. `--brand`
  (#FF4500) is punctuation for the wordmark mark only. `--reader-link` is the
  only green, scoped to `.reader-content`.
- **Type**: body/UI uses the platform system stack (`--font-sans`); display
  headings and numerals use Outfit (`--font-display` / `--font-numeric`).
  CJK resolves to PingFang / YaHei before bundled Noto.
- **Geometry**: radii are 6/8/10/12/16 (`--radius-sm … --radius-2xl`), never
  pills for controls. One width contract: `--app-content-max` (1200px),
  `--app-content-wide-max` (VideoPlay widescreen only), `--app-content-form-max`
  (640px), `--app-content-reading-max` (704px). Gutters and section gaps are
  continuous `clamp()` ranges.
- **Motion**: `--ease-out` is the fluid curve `cubic-bezier(.16,1,.3,1)`;
  springs are reserved for real momentum. Page changes use one `page-settle`
  transition (enter 240ms with a 6px rise, leave 160ms opacity-only) instead
  of directional slides. Insert/remove transitions desync opacity from
  position. Shared hover fills (“跳跃”) are one moving layer per group, with a
  200ms leave grace and a reduced-motion fallback.
- **Surfaces**: `.app-card`, `.app-list-row`, `.app-table-row`,
  `.app-media-frame` are the only shells; features compose them instead of
  re-declaring borders, radii, and backgrounds.

## Conventions

- **Typography**: `font-size` outside shared/ui and the video-player
  sub-theme should use a `--app-text-*` token. Prefer the semantic Tailwind
  aliases (`text-body`, `text-meta`, `text-secondary`, `text-eyebrow`,
  `text-section`, `text-page-title`) over the numeric `text-*` scale, which is
  offset from `--app-text-*`.
- **Overlays**: floating surfaces use the shared primitives (Dialog modal,
  Popover / DropdownMenu anchored, Tooltip annotation); avoid raw
  `Teleport` / `position: fixed` in feature code.
- **Colors**: semantic tokens only — raw Tailwind palette classes and raw
  hex values are lint errors (design-token ESLint rule) outside token
  definitions.

> 2026-10-23: the static `check:font-size` / `check:overlays` gates and the
> fixture-based `visual:review` harness were removed. They enforced token
> *usage*, not visual quality — the font-size codemod renamed existing values
> without changing rendered pixels, and the visual harness only compared a
> synthetic SVG against itself. `check:theme` was removed the next day for the
> same reason: it policed declaration shape, not rendered output. Treat the
> rules above as review conventions. Judge visual quality with real screenshots
> at 1280/1440/2560 in both themes.

## Component gallery

`/dev/ui` (dev builds only, `src/app/dev/UiGallery.vue`) renders every
primitive in its variants, plus the app type scale, radii, the four surface
recipes (`app-card`, `app-list-row`, `app-table-row`, `app-media-frame`) and a
live HoverFill scope. New components get verified there before entering
product pages; review it in both themes.

## Extension rules

- A component belongs in `shared/ui` when two or more features need its
  behavior; a one-off visual treatment stays in the feature.
- Primitives wrap reka-ui parts for behavior but own their markup classes;
  consumer CSS may scope-adjust via tokens, never by restyling `sq-*`
  internals.
- The video player is a declared **sub-theme** (`--sp-*`,
  `video-player/themes/`): it reads app semantic tokens only through the
  `--sp-theme-*` bridge block in `variables.css` and may otherwise stay
  opaque and dark. Its `font-size` and fixed-overlay usage is exempt from
  the conventions above.
