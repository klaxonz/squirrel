# Cinematic Shadcn Unification Design

**Date:** 2026-03-22

**Status:** Approved

## Problem

`squirrel-frontend` already has two useful foundations:

- a global light/dark theme contract in `src/styles/index.css`
- a local `shadcn-vue` component set under `src/components/ui/*`

The visual fragmentation now happens above that layer. App shell, feed pages, auth pages, and playback surfaces still define their own local visual language. The result is a half-unified product:

- some controls use `shadcn-vue`, others reimplement button, dialog, menu, or switch behavior
- shell surfaces and high-traffic pages do not share the same spacing, elevation, or action hierarchy
- the product still reads more like a mixed admin tool than a premium video application

For a video site, this is the wrong emphasis. The interface should feel like a content platform first and a management console second.

## Approved Direction

The approved direction is:

- style direction: `cinematic editorial`
- implementation direction: `shadcn-vue first for interaction primitives`
- theme requirement: `light + dark + system`, with both themes feeling like the same brand

This is not a full “turn every surface into stock shadcn” migration. The intent is:

- unify interaction primitives with `shadcn-vue`
- keep content-heavy surfaces custom where needed
- make every page feel like one coherent video product

## Goals

- Standardize interaction primitives on `shadcn-vue` contracts.
- Unify app shell, feed controls, dialogs, menus, and settings behavior.
- Redesign the highest-traffic pages to match a cinematic editorial visual system.
- Make light and dark themes equally intentional instead of one being a fallback.
- Preserve video-first UX for playback and content cards.

## Non-Goals

- Rewriting player runtime logic.
- Replacing every custom layout with generic shadcn cards.
- Introducing a new dependency stack or a parallel design system.
- Refactoring backend-facing data flow as part of the redesign.

## Visual System

### Brand Mood

The product should feel like a curated media workspace:

- warm editorial light theme for daytime browsing
- ink-and-charcoal dark theme for immersive viewing
- restrained amber/copper emphasis for actions and highlights

The design should avoid:

- pure white and pure black application surfaces
- blue/purple “AI dashboard” accents
- generic card grids with identical visual weight

### Theme Rules

Both themes must share one brand identity.

**Light theme**

- background: warm paper / soft stone
- surfaces: slightly elevated, low glare
- emphasis: amber-copper actions and focus
- text: neutral charcoal, not cold gray

**Dark theme**

- background: ink slate / charcoal
- surfaces: layered, slightly warm, not neon
- emphasis: same amber-copper family, not a different accent palette
- text: warm neutral off-white, not blue-white

### Shared Rules Across Themes

- identical component hierarchy
- identical focus behavior
- identical action semantics
- identical spacing rhythm and layout structure

Only luminance and transparency should shift between themes, not product identity.

## Component Strategy

### Must Standardize On `shadcn-vue`

- `Button`
- `Input`
- `Textarea`
- `Select`
- `Tabs`
- `Dialog`
- `Sheet`
- `DropdownMenu`
- `Tooltip`
- `Alert`
- `Badge`
- `Card`
- `Switch`

These components become the single interaction language for the app.

### May Stay Custom But Must Reuse The Same Tokens And Interaction Rules

- `VideoPlayer`
- feed video cards
- channel cards
- shell navigation items
- playback action strip

These areas may remain custom because they are content-first, but they must inherit the same tokens, borders, focus states, hover states, and elevation rules.

## Shell Strategy

The shell must look like one product before individual pages can look unified.

### App Shell

Files in scope:

- `src/App.vue`
- `src/styles/index.css`
- `src/components/layout/Sidebar.vue`
- `src/components/layout/SidebarMenuItem.vue`
- `src/components/layout/GlobalSearchBar.vue`
- `src/components/layout/MobileNav.vue`

Changes:

- unify page width, container rhythm, and topbar treatment
- turn global search into a first-class editorial control bar
- make sidebar and mobile nav feel premium but quiet
- remove one-off visual accents that do not map to shared tokens

## Page Strategy

### 1. Latest Videos

Purpose: the content homepage.

Changes:

- convert the top control strip into a unified editorial toolbar
- align tabs, selects, refresh, and filters to one component hierarchy
- refine video grid rhythm, loading states, alerts, and empty states
- retain content density while increasing polish

### 2. Video Play

Purpose: the immersive watch page.

Changes:

- keep the player as the hero surface
- convert action controls to shared `Button` and `DropdownMenu` semantics
- align metadata and related content with the same editorial system
- keep both light and dark modes immersive without splitting product identity

### 3. Subscribed

Purpose: the channel gallery.

Changes:

- align its control strip with the homepage toolbar
- convert channel settings interactions to `Dialog` or `Sheet`
- make channel cards feel like media entities, not dashboard tiles
- standardize status badges, action buttons, and loading feedback

### 4. Login And Register

Purpose: the brand entry point.

Changes:

- keep the cinematic atmosphere
- replace custom form primitives with `Input`, `Button`, `Card`, `Alert`
- make auth pages visually consistent with the rest of the application shell

### 5. Settings

Purpose: the brand and theme control surface.

Changes:

- keep existing theme mode support
- align cards, switches, status chips, and section navigation to shared primitives
- make theme previews accurately communicate light/dark brand mood

## Interaction Rules

- Primary actions should feel warm, confident, and visually heavier than today.
- Secondary actions should use surface contrast instead of loud color.
- Overflow actions should move into `DropdownMenu` instead of ad hoc popups.
- Modal editing should use `Dialog`; utility side panels should use `Sheet`.
- Hover and focus states must look consistent across shell, feed, and settings.

## Responsive Rules

- desktop: preserve wide media presentation and generous content gutters
- tablet: keep controls grouped but reduce secondary chrome
- mobile: adapt layouts instead of hiding important actions

The UI should still feel intentionally designed on small screens, not merely compressed.

## Verification

The redesign is successful when:

- `shadcn-vue` primitives are the default path for buttons, dialogs, tabs, inputs, and menus
- app shell, feed pages, playback, and auth screens read as one product
- light and dark themes both feel cinematic and branded
- the UI no longer looks like a partially styled admin console
- `npm run typecheck` and `npm run build:check` pass
- manual route walkthrough confirms no broken shell states on key pages

## Risks

- aggressive primitive unification can flatten content-heavy surfaces if applied mechanically
- playback page polish may drift into over-styling unless player logic stays isolated
- some old local CSS may visually conflict with new primitives until removed or rewritten
- mobile shell changes may expose spacing bugs if container rules are not centralized

## Decision

Proceed with a mixed strategy:

- `shadcn-vue` becomes the mandatory interaction layer
- shell and high-traffic pages are redesigned around a cinematic editorial system
- custom media surfaces remain custom only where they materially improve the video experience

This design supersedes narrower same-day docs that only covered theme token tuning or isolated `shadcn-vue` migration work.
