---
name: Squirrel Frontend
description: Desktop-first media subscription and playback control surface
colors:
  background-dark: "hsl(28 10% 7%)"
  foreground-dark: "hsl(28 10% 95%)"
  card-dark: "hsl(28 8% 9%)"
  sidebar-dark: "hsl(28 8% 8%)"
  primary-amber-dark: "hsl(28 90% 58%)"
  muted-foreground-dark: "hsl(28 6% 62%)"
  border-dark: "hsl(28 7% 16%)"
  background-light: "hsl(28 30% 99%)"
  sidebar-light: "hsl(28 22% 96%)"
  foreground-light: "hsl(28 10% 10%)"
  card-light: "hsl(0 0% 100%)"
  primary-amber-light: "hsl(28 88% 50%)"
  muted-foreground-light: "hsl(28 5% 42%)"
  border-light: "hsl(28 12% 89%)"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "1.6875rem"
    fontWeight: 600
    lineHeight: 1.15
    letterSpacing: "-0.02em"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "1.25rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "0"
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 600
    lineHeight: 1.25
    letterSpacing: "0"
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace"
rounded:
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "10px"
spacing:
  xs: "0.25rem"
  sm: "0.5rem"
  md: "1rem"
  lg: "1.5rem"
  xl: "2rem"
components:
  button-primary:
    backgroundColor: "{colors.primary-amber-dark}"
    textColor: "hsl(28 10% 6%)"
    rounded: "{rounded.md}"
    padding: "0.5rem 1rem"
    height: "2.25rem"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.muted-foreground-dark}"
    rounded: "{rounded.md}"
    padding: "0.5rem 1rem"
    height: "2.25rem"
  input-default:
    backgroundColor: "{colors.card-dark}"
    textColor: "{colors.foreground-dark}"
    rounded: "{rounded.md}"
    padding: "0.5rem 0.75rem"
    height: "2.25rem"
  card-default:
    backgroundColor: "{colors.card-dark}"
    textColor: "{colors.foreground-dark}"
    rounded: "{rounded.lg}"
    padding: "1rem"
  badge-status:
    backgroundColor: "hsl(28 90% 58% / 0.10)"
    textColor: "{colors.primary-amber-dark}"
    rounded: "{rounded.md}"
    padding: "0.125rem 0.5rem"
---

# Design System: Squirrel Frontend

## 1. Overview

**Creative North Star: "The Private Media Operations Desk"**

Squirrel's target interface is a desktop-first control surface for a personal media archive. The current codebase provides product structure, route boundaries, reusable components, and technical tokens; it is not automatically the visual ideal. When current UI choices feel cramped, decorative, inconsistent, or weak in hierarchy, redesign them instead of preserving them.

The target system borrows the viewing comfort of a dark media library and the precision of an operations console: quiet chrome, clear state, dense but calm navigation, and media content as the visual anchor. Amber is the identity color and should appear on primary actions, selected state, focus, playback emphasis, and status accents. Surfaces stay close to the background so thumbnails, lists, runtime health, and playback controls remain readable.

**Key Characteristics:**
- Desktop app shell with fixed title bar, sidebar, header, scroll root, and persistent playback surfaces.
- Dark-first amber-on-warm-neutral theme with a light mode that preserves the same hue axis.
- Dense task UI using compact controls, visible keyboard focus, short state motion, and predictable navigation.
- Media-led content screens supported by operational settings, logs, runtimes, and scheduled-task management.
- Current implementation is a diagnostic baseline, not a preservation contract.

## 2. Colors

The palette runs on one warm amber hue axis: near-black warm neutrals for dark mode, near-white warm neutrals for light mode, and a single saturated amber accent for identity and action.

### Primary
- **Archive Amber** (`hsl(28 90% 58%)` dark, `hsl(28 88% 50%)` light): primary buttons, active navigation icons, focus rings, connected status emphasis, brand badge, and rare high-value highlights.

### Neutral
- **Projection Black** (`hsl(28 10% 7%)`): dark-mode app background and main reading surface. The sidebar uses a subtly lifted warm neutral so navigation remains scannable without becoming a floating panel.
- **Panel Charcoal** (`hsl(28 8% 9%)`): cards, inputs, popovers, and table containers in dark mode.
- **Warm White** (`hsl(28 30% 99%)`): light-mode background without changing the amber identity.
- **Muted Ink** (`hsl(28 6% 62%)` dark, `hsl(28 5% 42%)` light): secondary labels, inactive icons, metadata, and placeholder text.
- **Hairline Warm Border** (`hsl(28 7% 16%)` dark, `hsl(28 12% 89%)` light): dividers, card borders, input strokes, and sidebar separation.

### Named Rules

**The Amber Is State Rule.** Use amber for selection, focus, primary action, brand identity, and concrete status. Do not use amber as background decoration.

**The Thumbnail Wins Rule.** Keep surrounding surfaces restrained so media artwork and thumbnails carry visual richness.

**The Current Palette Is Not Sacred Rule.** The existing amber/warm-neutral tokens may be reused because they fit the product, not because they already exist. If a screen fails contrast, hierarchy, or mood, change the application of the tokens rather than copying the old treatment.

## 3. Typography

**Display Font:** Inter with system sans fallbacks
**Body Font:** Inter with the same system sans fallbacks
**Label/Mono Font:** JetBrains Mono for logs, ids, counters, and tabular operational values

**Character:** Inter owns the complete product interface, including headings, controls, dense lists, navigation, labels, and data. Hierarchy comes from size, weight, spacing, and contrast instead of switching to an editorial display face.

### Hierarchy
- **Display** (600, 27px, 1.15): top page headings and primary empty-state titles.
- **Headline** (600, 20px, 1.25): section headers, settings groups, and major panel headings.
- **Title** (600, 17px, 1.3): cards, lists, and compact content modules.
- **Body** (400-500, 14px, 1.5): descriptions, rows, settings copy, and form support text.
- **Label** (600, 12-13px, no negative tracking): tabs, badges, sidebar labels, buttons, metadata labels, and menu items.
- **Micro Label** (8-10px): duration badges, timestamps, dense secondary metadata only.

### Named Rules

**The Product Type Rule.** Use fixed rem sizes for product UI. Avoid fluid type on app surfaces; density and stability matter more than dramatic scaling.

**The Unified Product Type Rule.** Use the shared Inter stack for headings and body copy. Do not introduce a separate display face; create hierarchy with the established type scale and weights.

**The Existing Heading Scale Is A Starting Point Rule.** Keep the current scale only where it produces clear hierarchy. If a page looks visually flat or cramped, redesign the hierarchy first; do not normalize the flaw into new screens.

## 4. Elevation

Squirrel uses a hybrid of tonal layering and small structural shadows. Resting surfaces rely on background, border, and subtle tonal contrast. Shadows appear for popovers, hover lift, brand badges, and transient overlays where depth clarifies stacking.

### Shell Canvas

The desktop shell is **one continuous canvas**, not a stack of floating cards.

- Title bar, workspace, workbench secondary panes, headers, and toolbars rest on `--background` (or transparent over it). The primary sidebar may use the quiet `--sidebar` tint to distinguish persistent navigation.
- Regional hierarchy is hairline borders only (`--app-hairline` / sidebar border). Do not tint secondary panes with `--card` to invent depth.
- No outer frame padding + gap that turns sidebar and workspace into two floating islands.
- No full border + radius + panel shadow on shell chrome. Those treatments are reserved for true overlays (menus, dialogs, popovers) and media item cards.

### Shadow Vocabulary
- **Surface Hairline** (`0 1px 2px hsl(var(--foreground) / 0.04)`): tables and small resting content surfaces — not shell regions.
- **Primary Button Lift** (`0 1px 2px hsl(var(--primary)/0.3), 0 0 0 1px hsl(var(--primary)/0.5) inset`): primary action at rest.
- **Primary Button Hover** (`0 2px 8px hsl(var(--primary)/0.35)`): primary action hover only.
- **Popover Lift** (`0 8px 24px hsl(var(--foreground) / 0.14), 0 24px 56px hsl(var(--foreground) / 0.10)`): menus, search suggestions, and dropdowns.
- **Brand Glow** (`0 8px 24px hsl(var(--primary) / 0.32)` plus hairline): brand badge only.

### Named Rules

**The Single Canvas Rule.** Shell regions remain flush and structurally continuous. A subtle sidebar tint is allowed, but split structure still comes from alignment and hairlines rather than nested cards, inset panels, or dual floating columns.

**The Flat Until It Moves Rule.** Keep cards and panels nearly flat at rest. Use elevation to explain overlays, focus, hover, or brand identity, not to decorate every container.

**The Effects Must Justify Themselves Rule.** Existing blur, noise, glow, backdrop filters, and cinematic treatments are allowed only when they improve readability, depth, or media focus. Remove them when they make the product feel ornamental.

## 5. Components

### Buttons
- **Shape:** compact rounded rectangles using `--radius-md` (`6px`); icon buttons may be square or full-pill only when the control is circular by affordance.
- **Primary:** amber background with primary foreground, 36px default height, 14px semibold text, subtle inset outline and hover glow.
- **Secondary / Outline:** neutral tonal surfaces or transparent backgrounds with border emphasis; use when the action is not the next obvious step.
- **Ghost:** muted text at rest, accent background on hover, foreground text on hover.
- **States:** disabled opacity is 40%; active press scales to `0.985`; focus uses a ring bound to `--ring`.

### Inputs / Fields
- **Style:** 36px height, `--radius-md`, card background, input border, 14px text, 12px horizontal padding.
- **Focus:** border shifts to `--ring` with a low-alpha ring; do not replace it with only color or glow.
- **Search:** global search is a compact command/search hybrid with optional local/remote scope toggle, recent searches, suggestions, and `Cmd/Ctrl+K` focus behavior.

### Cards / Containers
- **Corner Style:** `--radius-lg` (`8px`) for app surfaces and `--radius-xl` (`10px`) for richer media cards.
- **Background:** `--card` or muted surface layers; no nested card shells unless the inner element is a real repeated item.
- **Border:** `border-border/60` or `--app-surface-border`; use hairlines for structure.
- **Internal Padding:** default `1rem`, wider only for empty states or detail surfaces.

### Badges / Chips
- **Style:** compact rounded-md pill-like labels with 1px border, 12px text, and low-alpha state backgrounds.
- **State:** status variants use success, warning, destructive, or amber with text plus context; never rely on color alone.

### Navigation
- **System title bar:** owns shell-level navigation controls: sidebar visibility, application back, application forward, and window controls. These actions do not belong inside page headers or sidebar content.
- **Sidebar:** fixed `15rem` desktop rail that never resizes, reflows, or changes its internal menu geometry. Sidebar visibility is controlled by the workspace layer: expanded state positions the workspace at the rail's right edge; collapsed state moves the opaque workspace to `left: 0`, progressively covering the stationary rail. Covered sidebar content is inert and removed from the accessibility tree. Brand sits at the top, home is the immediate navigation entry, grouped navigation scrolls as one list, and settings stays fixed at the bottom. Search remains a header-level global action and is not duplicated in the sidebar.
- **Workspace:** continuous with the shell background. No outer card frame, radius, or panel shadow around the main content column.
- **Workbench panes:** secondary sidebars (订阅频道, 播放列表, RSS entry list, settings nav) stay transparent on the same canvas; only a vertical hairline divides list from content.
- **Header:** fixed height with history controls, current page title, contextual search, and user entry point. Flat `--background`, single bottom hairline. It should not repeat breadcrumbs already represented by the sidebar.
- **Tabs / Segmented Controls:** use shared `Tabs` / `TabsList` / `TabsTrigger` or `AppSegmentedControl`. Compact height, secondary track, active card surface, focus-visible ring. Do not invent a third tab look per feature.

### Skeletons
- **Style:** `AppSkeleton` is the single placeholder primitive. Use `--app-skeleton-base`, `--app-skeleton-shimmer`, and `--app-skeleton-radius`.
- **Motion:** shimmer is acceptable for list/grid loading. Respect reduced motion when adding new animated placeholders.

### Dialogs / Popovers
- **Role:** use for focused confirmation, command-like selection, search suggestions, and runtime detail. Prefer inline/progressive controls before adding a modal.
- **Stacking:** use the z-index tokens: dropdown, popover, sheet, dialog, toast, player overlay.

## 6. Do's and Don'ts

### Do:
- **Do** preserve the desktop-first shell: title bar, sidebar, app header, scroll root, and persistent playback surfaces.
- **Do** reuse existing CSS variables and Tailwind token mappings when they support the target design.
- **Do** change or remove existing visual treatments when they encode the current design problem.
- **Do** keep media thumbnails and titles visually dominant on content screens.
- **Do** show concrete runtime/auth/download/log state with useful next actions.
- **Do** keep transitions short: 120ms for control feedback, 180ms for page/panel transitions, 240ms for larger surfaces.
- **Do** verify keyboard focus on every custom interactive element.

### Don't:
- **Don't** add mobile-first breakpoints unless the task explicitly asks for mobile behavior.
- **Don't** float the sidebar and workspace as separate padded cards with gap, radius, and panel shadow.
- **Don't** tint workbench/secondary panes with `--card` just to mark regions; hairlines are enough.
- **Don't** use decorative gradient text, glassmorphism, diagonal stripes, or generic dashboard hero metrics.
- **Don't** create colored side-stripe cards or alert stripes; use full borders, icons, badges, or semantic copy.
- **Don't** make inactive UI saturated or high contrast; reserve emphasis for current state and action.
- **Don't** hide broken server, runtime, auth, or media states behind generic fallback copy.
- **Don't** introduce a new component vocabulary when `Button`, `Input`, `Badge`, `Card`, `AppSkeleton`, tabs, sidebar items, or existing layout primitives already cover the need.
- **Don't** treat existing pages as approved references. Use them to understand flow and constraints, then redesign the broken hierarchy, spacing, density, copy, and component behavior directly.
