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

## Hard rules

- **Typography**: `font-size` outside shared/ui and the video-player
  sub-theme must use a `--app-text-*` token. Enforced by
  `renderer/scripts/check-raw-font-size.mjs` (`npm run check:font-size`).
- **Overlays**: floating surfaces use the shared primitives (Dialog modal,
  Popover / DropdownMenu anchored, Tooltip annotation). Raw `Teleport` /
  `position: fixed` in feature code is forbidden; declared exceptions live
  in `renderer/scripts/check-raw-overlays.mjs` (`npm run check:overlays`).
  Both gates run via `npm run check`.
- **Colors**: semantic tokens only — raw Tailwind palette classes and raw
  hex values are lint errors (design-token ESLint rule) outside token
  definitions.

## Component gallery

`/dev/ui` (dev builds only, `src/app/dev/UiGallery.vue`) renders every
primitive in its variants. New components get verified there before
entering product pages.

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
  the gates above.
