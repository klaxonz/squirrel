# Compact Shadcn Dashboard Redesign Design

**Date:** 2026-03-26

**Status:** Approved

## Problem

`squirrel-frontend` already contains a usable `shadcn-vue` primitive layer under `src/components/ui/*`, but the product still does not read as one coherent application.

The current problems are above the primitive layer:

- app shell, sidebar, top bar, auth, feed, playback, and system pages still use different visual languages
- the interface mixes compact utility surfaces with oversized decorative containers
- page-level information hierarchy is inconsistent, so the product feels stitched together instead of designed as one dashboard
- some pages already moved toward `shadcn-vue`, but the shell and highest-frequency routes still look custom in incompatible ways

The result is not a clear `shadcn` product and not a clear media product either. It is visually fragmented.

## Approved Direction

The approved direction is:

- style direction: `shadcn official dashboard first`
- product tone: `compact content workbench`
- layout permission: `restructure page hierarchy and navigation groups where it materially improves clarity`
- density requirement: `small and tight, not spacious or oversized`

This is not a pure “replace styles with stock shadcn classes” pass.

The design should borrow the discipline of the official `shadcn/ui` dashboard examples:

- restrained surfaces
- clear borders and panel hierarchy
- compact controls
- neutral, low-drama color usage
- consistent page headers and action placement

At the same time, it must still support a product centered on videos, subscriptions, playback history, and sync workflows.

## Goals

- Unify the entire frontend on one compact `shadcn-vue` dashboard language.
- Make shell, navigation, page headers, cards, tables, forms, dialogs, and filters feel like one system.
- Reduce oversized controls, excessive rounding, and decorative shell effects.
- Preserve content browsing efficiency for videos and subscriptions.
- Allow page hierarchy and navigation structure to be reorganized where needed.
- Keep the redesign focused on UI structure and presentation, not backend or route behavior changes.

## Non-Goals

- Rewriting API contracts or backend data flow.
- Replacing playback runtime logic.
- Building a new design system parallel to `shadcn-vue`.
- Turning all content pages into plain admin tables.
- Doing opportunistic refactors unrelated to the redesign.

## Visual System

### Brand Mood

The product should feel like a clean, compact dashboard for managing and browsing content:

- neutral and restrained rather than cinematic or decorative
- sharper hierarchy through borders, spacing, and typography instead of glow and large shadows
- compact, desk-like, tool-oriented, but not cold or sterile

The UI should avoid:

- large pill buttons and oversized inputs
- heavy floating panels and glass-like shell effects
- overly large border radii
- loud gradients, glows, or ambient decoration in routine work surfaces
- inconsistent sizing between feed pages and system pages

### Density Rules

Compactness is a first-class requirement.

The default UI density should be one step tighter than many stock `shadcn` examples:

- buttons default to `sm` sizing unless a larger call to action is truly needed
- inputs, selects, tabs, filter chips, and dropdown triggers should feel narrow and efficient
- page headers should be thin and structured, not tall hero blocks
- cards should be used for grouping, not as the default wrapper for everything
- tables and lists should carry more of the product than oversized cards

### Tokens And Surface Rules

The palette should stay neutral and dashboard-like:

- light theme remains primary
- emphasis color stays controlled and semantic
- borders and surface contrast do most of the hierarchy work
- shadows remain soft and secondary

Shared rules:

- reduce application-wide radius scale toward `md/lg`
- reduce shadow intensity across shell and controls
- keep text and controls visually compact
- standardize hover, focus, and selected states through shared semantic tokens

## Information Architecture

The user approved structural reorganization where it improves clarity.

### Navigation Strategy

The shell should separate the product into two clear groups:

- content workspace
- system workspace

Recommended top-level groups:

- `Content`: Latest Videos, Subscribed, History, Playback entry points
- `Operations`: Sync Center, Monitoring, Scheduled Tasks
- `System`: Plugins, Logs, Settings

This grouping should be reflected in both desktop sidebar and mobile navigation.

### Page Header Contract

All non-auth pages should share one header contract:

- page title
- one short supporting line only where needed
- primary actions on the right
- filters or search directly below only when the route needs them

This replaces the current pattern where each page invents its own head area.

## Shell Strategy

Files primarily in scope:

- `src/App.vue`
- `src/styles/index.css`
- `src/components/layout/Sidebar.vue`
- `src/components/layout/SidebarMenuItem.vue`
- `src/components/layout/GlobalSearchBar.vue`
- `src/components/layout/MobileNav.vue`
- `src/constants/sidebar.ts`

Changes:

- replace the current decorative shell treatment with a thinner dashboard shell
- tighten topbar height, page gutters, and navigation sizing
- make global search part of a compact page control row rather than a prominent visual feature
- standardize sidebar active, hover, and collapsed states around `shadcn` semantics

The shell should feel calm and repeatable. If the shell is still expressive, the rest of the app cannot look unified.

## Page Strategy

### 1. Latest Videos

Purpose: the main content workbench.

Changes:

- rebuild the toolbar as a compact filter/action strip
- tighten tabs, filters, and refresh controls
- reduce container thickness around the list
- keep content browsing efficient instead of converting the page into a generic admin table

### 2. Subscribed

Purpose: subscription library and channel management.

Changes:

- align page header and controls to the shell contract
- simplify channel gallery/list presentation
- unify dialogs, menus, and actions on shared primitives
- preserve content identity while removing oversized card treatment

### 3. History

Purpose: playback activity review.

Changes:

- bring it onto the same page header, filter, and compact list contract as content pages
- make it feel like part of the same dashboard instead of a special-case route

### 4. Video Play

Purpose: focused playback inside the same product language.

Changes:

- keep the player dominant, but simplify adjacent chrome
- make metadata, side panels, and actions read like compact dashboard surfaces
- preserve playback-specific affordances without reverting to decorative theming

### 5. System Pages

Pages:

- `SyncCenter`
- `Monitoring`
- `ScheduledTasks`
- `PluginManager`
- `LogViewer`
- `Settings`

Changes:

- unify all page headers
- standardize panel structure
- prefer compact cards, tables, badges, and section blocks
- reduce visual drift between analytics-like pages and operational pages

These pages should be the closest to the official `shadcn` dashboard examples.

### 6. Auth Pages

Pages:

- `Login`
- `Register`

Changes:

- simplify the current auth presentation
- keep brand recognition but drop oversized hero treatment
- use compact form controls and restrained supporting copy

Auth should feel like the entry point to the same application, not a different visual system.

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
- `Table`
- `Switch`
- `Label`

These components define the default interaction contract for the redesign.

### May Stay Custom But Must Follow Shared Rules

- video list items
- channel items
- player-adjacent surfaces
- shell navigation rows
- route-specific toolbars that depend on existing behavior

Custom components may stay custom only when they serve content density or route-specific behavior. They must still inherit the same spacing, radius, border, focus, and hover rules.

## Interaction Rules

- Primary actions should be visually clear but not oversized.
- Secondary actions should read as compact controls, not decorative pills.
- Overflow behavior should prefer `DropdownMenu`.
- Edit flows should use `Dialog`; side utility flows may use `Sheet`.
- Focus states must be consistent across sidebar, filters, dialogs, and tables.
- Selection states should rely on shared semantic colors and borders, not one-off CSS highlights.

## Responsive Rules

- desktop: compact dashboard shell with stable left navigation and thin page headers
- tablet: keep page actions accessible while reducing horizontal spread
- mobile: preserve core actions, with compact sheet/drawer patterns where needed

Mobile adaptation should simplify structure, not merely shrink desktop chrome.

## Verification

The redesign is successful when:

- shell, content pages, operations pages, and auth routes clearly look like one product
- component sizing feels compact across the app
- `shadcn-vue` primitives are the default interaction layer
- page headers, filters, and action placement follow one repeatable contract
- content routes still browse well despite the tighter dashboard language
- `npm run typecheck` and `npm run build` pass

## Risks

- pushing too hard toward stock dashboard patterns can flatten content-heavy routes
- reducing size aggressively can harm readability if typography and spacing are not tuned together
- old local CSS may continue to leak oversized radius, spacing, or effects until fully normalized
- system pages and video pages may drift apart again if shell and page-header contracts are not enforced first

## Decision

Proceed with a compact `shadcn` dashboard redesign:

- official `shadcn` dashboard discipline is the primary reference
- compact density is mandatory
- page hierarchy may be reorganized where it improves clarity
- content pages keep media-specific structure only where it materially helps browsing

This design supersedes narrower visual experiments that emphasized cinematic styling or partial primitive migration without full shell unification.
