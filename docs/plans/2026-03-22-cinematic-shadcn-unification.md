# Cinematic Shadcn Unification Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Unify `squirrel-frontend` around `shadcn-vue` interaction primitives and a cinematic editorial visual system across shell, feed, playback, subscription, auth, and settings pages, while preserving robust light and dark theme support.

**Architecture:** Keep `src/components/ui/*` as the only shared primitive layer, then retune shell-level layout and retheme high-traffic views on top of the existing route and data flow. Content-heavy areas remain custom where necessary, but must consume the same design tokens, component semantics, and interaction hierarchy.

**Tech Stack:** Vue 3 + Vite + TailwindCSS + shadcn-vue + Pinia + Vue Router + TypeScript

---

## Task 0: Create A Dedicated Worktree And Capture Baseline

**Files:**
- None

**Step 1: Create a worktree**

Run from repo root:

```powershell
git worktree add .worktrees/cinematic-shadcn-unification -b feat/cinematic-shadcn-unification
```

Expected:
- `.worktrees/cinematic-shadcn-unification` exists
- the new branch is checked out in the worktree

**Step 2: Enter the worktree**

```powershell
cd .worktrees/cinematic-shadcn-unification
```

**Step 3: Install frontend dependencies if needed**

```powershell
cd squirrel-frontend
npm install
```

Expected: `npm` exits with code 0.

**Step 4: Run baseline verification**

```powershell
npm run typecheck
npm run build:check
```

Expected: both commands exit with code 0.

**Step 5: No commit**

This task only records baseline evidence.

---

## Task 1: Normalize Shared Primitive Styling

**Files:**
- Modify: `squirrel-frontend/src/styles/index.css`
- Modify: `squirrel-frontend/src/components/ui/button/Button.vue`
- Modify: `squirrel-frontend/src/components/ui/input/Input.vue`
- Modify: `squirrel-frontend/src/components/ui/card/Card.vue`
- Modify: `squirrel-frontend/src/components/ui/badge/Badge.vue`
- Modify: `squirrel-frontend/src/components/ui/alert/Alert.vue`
- Modify: `squirrel-frontend/src/components/ui/tabs/TabsList.vue`
- Modify: `squirrel-frontend/src/components/ui/tabs/TabsTrigger.vue`
- Modify: `squirrel-frontend/src/components/ui/dropdown-menu/DropdownMenuContent.vue`
- Modify: `squirrel-frontend/src/components/ui/dialog/DialogContent.vue`
- Modify: `squirrel-frontend/src/components/ui/sheet/SheetContent.vue`
- Modify: `squirrel-frontend/src/components/ui/switch/Switch.vue`

**Step 1: Rewrite token emphasis for both themes**

Update `src/styles/index.css` so the shared variables follow the approved brand:

```css
:root {
  --background: 30 27% 95%;
  --card: 28 31% 98%;
  --primary: 24 63% 49%;
  --ring: 25 84% 54%;
}

.dark {
  --background: 220 26% 10%;
  --card: 220 24% 13%;
  --primary: 28 78% 59%;
  --ring: 28 90% 62%;
}
```

Do not reintroduce pure `#000` / `#fff` for app surfaces.

**Step 2: Calibrate primitive variants**

Adjust component variant classes so `Button`, `Input`, `Card`, `Badge`, `Alert`, `Tabs`, `Dialog`, `Sheet`, and `DropdownMenu` share:

- pill/rounded rhythm
- consistent hover elevation
- stronger focus ring visibility
- quieter neutral borders
- identical dark/light semantic meaning

Representative target for a primary button:

```ts
'bg-primary text-primary-foreground shadow-[0_18px_40px_hsl(var(--surface-shadow))] hover:translate-y-[-1px] hover:brightness-[1.02]'
```

**Step 3: Verify typecheck and build**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Expected: both commands pass.

**Step 4: Commit**

```powershell
git add squirrel-frontend/src/styles/index.css squirrel-frontend/src/components/ui
git commit -m "feat(frontend): normalize cinematic shadcn primitives"
```

---

## Task 2: Unify App Shell And Global Navigation

**Files:**
- Modify: `squirrel-frontend/src/App.vue`
- Modify: `squirrel-frontend/src/components/layout/Sidebar.vue`
- Modify: `squirrel-frontend/src/components/layout/SidebarMenuItem.vue`
- Modify: `squirrel-frontend/src/components/layout/GlobalSearchBar.vue`
- Modify: `squirrel-frontend/src/components/layout/MobileNav.vue`
- Modify: `squirrel-frontend/src/constants/sidebar.ts`

**Step 1: Centralize shell spacing**

Move repeated page container rhythm into `App.vue` and shared classes:

```vue
<main class="flex-1 relative flex min-h-0 flex-col">
  <div v-if="showGlobalSearch" class="topbar" ref="topbarRef">
    <GlobalSearchBar ... />
  </div>
  <div class="page-container flex-1 min-h-0">
    ...
  </div>
</main>
```

Target behavior:

- topbar reads as editorial control strip, not plain input row
- consistent horizontal padding at app-shell level
- shell width and spacing do not drift per page

**Step 2: Replace ad hoc search input styling with primitive styling**

In `GlobalSearchBar.vue`, switch the raw `<input>`-led styling to shared `Input` and `Button` semantics, while preserving debounced search behavior.

**Step 3: Tune sidebar and mobile nav**

Make navigation feel premium but quiet:

- active item uses shared accent logic
- inactive item hover uses subtle translation and surface tint only
- icons, labels, and collapse state follow the same spacing scale

**Step 4: Verify key routes manually**

Run:

```powershell
cd squirrel-frontend
npm run dev
```

Check:

- `/videos/all`
- `/subscribed`
- `/settings`
- `/video/:id`

Expected: shell states work in both expanded and flyout layouts.

**Step 5: Run automated verification**

```powershell
npm run typecheck
npm run build:check
```

**Step 6: Commit**

```powershell
git add squirrel-frontend/src/App.vue squirrel-frontend/src/components/layout squirrel-frontend/src/constants/sidebar.ts
git commit -m "feat(frontend): unify cinematic app shell"
```

---

## Task 3: Rebuild Feed Toolbar On Shared Primitives

**Files:**
- Modify: `squirrel-frontend/src/components/feed/FeedToolbar.vue`
- Modify: `squirrel-frontend/src/components/feed/TabBar.vue`
- Modify: `squirrel-frontend/src/components/feed/SortButton.vue`
- Modify: `squirrel-frontend/src/components/feed/SiteFilter.vue`
- Modify: `squirrel-frontend/src/components/feed/NsfwFilter.vue`
- Modify: `squirrel-frontend/src/components/feed/RefreshButton.vue`

**Step 1: Move tab/filter controls to a single visual contract**

Use `Tabs`, `Button`, `Select`, and `DropdownMenu` semantics so the toolbar reads as one control band instead of a row of unrelated widgets.

Representative structure:

```vue
<div class="feed-toolbar">
  <Tabs ... />
  <div class="feed-toolbar__actions">
    <NsfwFilter />
    <SiteFilter />
    <SortButton />
    <RefreshButton />
  </div>
</div>
```

**Step 2: Keep existing emits stable**

Do not change public emitted events:

- `update:activeTab`
- `update:nsfw`
- `update:sortBy`
- `update:site`
- `tab-dblclick`
- `refresh`

**Step 3: Tune compact states**

Toolbar must stay coherent on tablet and mobile:

- preserve primary tabs
- collapse less-critical controls into compact primitives if necessary
- keep refresh accessible without relying on hover

**Step 4: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Expected: passes, and homepage/subscribed toolbar still functions.

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/components/feed/FeedToolbar.vue squirrel-frontend/src/components/feed/TabBar.vue squirrel-frontend/src/components/feed/SortButton.vue squirrel-frontend/src/components/feed/SiteFilter.vue squirrel-frontend/src/components/feed/NsfwFilter.vue squirrel-frontend/src/components/feed/RefreshButton.vue
git commit -m "refactor(frontend): unify feed toolbar primitives"
```

---

## Task 4: Redesign Latest Videos And Shared Video Cards

**Files:**
- Modify: `squirrel-frontend/src/views/LatestVideos.vue`
- Modify: `squirrel-frontend/src/components/feed/VideoItem.vue`
- Modify: `squirrel-frontend/src/components/feed/VideoList.vue`
- Modify: `squirrel-frontend/src/components/feed/ContextMenu.vue`
- Modify: `squirrel-frontend/src/styles/components/LatestVideos.css`
- Modify: `squirrel-frontend/src/styles/components/video-card.css`

**Step 1: Reframe the page as a content home**

`LatestVideos.vue` should:

- keep existing route and filter behavior
- use the rebuilt toolbar as the hero control surface
- standardize `Alert` placement and spacing
- use a shared content container rhythm

**Step 2: Upgrade `VideoItem.vue` without flattening it**

Preserve custom media-card behavior, but align it to shared rules:

- title and meta hierarchy use shared text scales
- hover/focus states use brand tokens instead of ad hoc blue text
- context actions move toward `DropdownMenu`-style semantics
- progress, duration, and NSFW handling remain intact

Replace hard-coded hover color patterns such as:

```vue
class="... hover:text-blue-500 ..."
```

with semantic brand classes tied to the same token family.

**Step 3: Make empty, loading, and error states coherent**

Use `Alert`, `Card`, and shared surface styling instead of per-component custom fallback blocks.

**Step 4: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Manual:

- `/videos/all`
- `/videos/unread`
- `/subscription/:id/all`

Check click-through, context menu, avatar fallback, and refresh behavior.

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/LatestVideos.vue squirrel-frontend/src/components/feed/VideoItem.vue squirrel-frontend/src/components/feed/VideoList.vue squirrel-frontend/src/components/feed/ContextMenu.vue squirrel-frontend/src/styles/components/LatestVideos.css squirrel-frontend/src/styles/components/video-card.css
git commit -m "feat(frontend): redesign cinematic feed surfaces"
```

---

## Task 5: Redesign The Subscription Gallery And Channel Settings Flows

**Files:**
- Modify: `squirrel-frontend/src/views/Subscribed.vue`
- Modify: `squirrel-frontend/src/components/dialogs/AddChannelDialog.vue`
- Modify: `squirrel-frontend/src/components/dialogs/ImportSubscriptionDialog.vue`
- Modify: `squirrel-frontend/src/components/ui/dialog/DialogContent.vue` (only if shared polish is still needed)

**Step 1: Convert the page into a media gallery**

Keep existing data behavior, but update the layout so channel cards feel like media entities:

- stronger top section hierarchy
- quieter but richer card surfaces
- action buttons aligned with the toolbar contract

**Step 2: Replace local modal styling with shared dialog/sheet primitives**

Current subscription settings flow should move from ad hoc overlay markup to `Dialog` or `Sheet`, depending on which better fits the content volume.

Recommended: use `Dialog` first, because the settings set is compact.

**Step 3: Keep state and API behavior stable**

Do not change:

- `loadSubscriptions`
- `handleRefreshSubscription`
- `retryRefresh`
- `unsubscribe`
- search event behavior

Only reframe presentation and interaction primitives.

**Step 4: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Manual:

- `/subscribed`
- add subscription dialog
- import subscription dialog
- open channel settings
- toggle NSFW
- trigger refresh and retry

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/Subscribed.vue squirrel-frontend/src/components/dialogs/AddChannelDialog.vue squirrel-frontend/src/components/dialogs/ImportSubscriptionDialog.vue
git commit -m "feat(frontend): redesign subscription gallery and dialogs"
```

---

## Task 6: Redesign The Playback Page And Align Player Theming

**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`
- Modify: `squirrel-frontend/src/components/video-player/themes/variables.css`
- Modify: `squirrel-frontend/src/components/video-player/themes/light.css`
- Modify: `squirrel-frontend/src/components/video-player/themes/dark.css`

**Step 1: Keep playback layout logic intact**

Do not rewrite:

- widescreen state handling
- previous/next behavior
- playback orchestration
- reporting and subtitle wiring

**Step 2: Standardize playback actions**

Move action strip semantics onto the shared primitive hierarchy:

- primary content actions use shared button tokens
- overflow uses `DropdownMenu`-style treatment
- metadata and channel chips use shared badge/surface rules

**Step 3: Align player theme variables with the app brand**

Rewrite the light/dark player CSS variables so the player feels related to the shell:

- dark player: immersive charcoal with warm highlights
- light player: bright but not stark
- keep media surface black only where structurally necessary

**Step 4: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Manual:

- `/video/:id`
- toggle widescreen
- open overflow actions
- check related video list
- verify both light and dark themes

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/VideoPlay.vue squirrel-frontend/src/components/video-player/themes/variables.css squirrel-frontend/src/components/video-player/themes/light.css squirrel-frontend/src/components/video-player/themes/dark.css
git commit -m "feat(frontend): redesign playback page and player theme"
```

---

## Task 7: Unify Auth And Settings Surfaces

**Files:**
- Modify: `squirrel-frontend/src/views/Login.vue`
- Modify: `squirrel-frontend/src/views/Register.vue`
- Modify: `squirrel-frontend/src/views/Settings.vue`
- Modify: `squirrel-frontend/src/composables/useAppTheme.ts` (only if theme hydration behavior needs polish)
- Modify: `squirrel-frontend/src/lib/theme.ts` (only if utility changes are required)
- Modify: `squirrel-frontend/src/lib/theme.test.ts` (only if utility changes are required and test runner support already exists)

**Step 1: Switch auth forms to shared primitives**

Replace local auth form markup where practical with `Card`, `Input`, `Button`, and `Alert` usage, while preserving the cinematic hero layout.

**Step 2: Tune settings view to the same product language**

Keep existing sections and logic, but align:

- section navigation
- theme choice cards
- switches
- status chips
- card headers and spacing

**Step 3: Preserve theme-mode behavior**

Do not regress:

- `light`
- `dark`
- `system`

If utilities change, update their tests only if the project already supports the test command in the active branch. Do not add a new test framework in this pass.

**Step 4: Verify**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Manual:

- `/login`
- `/register`
- `/settings`
- switch between light, dark, and system

**Step 5: Commit**

```powershell
git add squirrel-frontend/src/views/Login.vue squirrel-frontend/src/views/Register.vue squirrel-frontend/src/views/Settings.vue squirrel-frontend/src/composables/useAppTheme.ts squirrel-frontend/src/lib/theme.ts squirrel-frontend/src/lib/theme.test.ts
git commit -m "feat(frontend): unify auth and settings surfaces"
```

---

## Task 8: Final Visual Regression Pass

**Files:**
- Modify: only files touched by polish findings

**Step 1: Run full verification**

```powershell
cd squirrel-frontend
npm run typecheck
npm run build:check
```

Expected: both commands pass.

**Step 2: Manual walkthrough**

Run:

```powershell
npm run dev
```

Check these routes in both light and dark themes:

- `/videos/all`
- `/subscribed`
- `/history`
- `/video/:id`
- `/settings`
- `/login`
- `/register`

Review:

- shell consistency
- focus states
- dialog and dropdown layering
- mobile layout
- hover states
- loading/error states

**Step 3: Make minimal fixes only**

No refactor. Only address visual regressions, broken spacing, or unreadable states.

**Step 4: Commit**

```powershell
git add -A
git commit -m "fix(frontend): polish cinematic shadcn unification"
```
