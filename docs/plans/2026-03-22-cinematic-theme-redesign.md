# Cinematic Theme Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the current grayscale-heavy frontend theme with a fully supported `light` / `dark` / `system` cinematic editorial theme across app chrome, shadcn surfaces, and the video player.

**Architecture:** Rebuild the semantic token system in `src/styles/index.css`, add a single runtime app theme controller rooted on `html.dark`, expose the theme choice in settings, and retune high-frequency UI surfaces to consume the new tokens. Bring the video player theme variables into the same palette family while keeping its dedicated immersion-oriented styling.

**Tech Stack:** Vue 3, Vite, Tailwind CSS, shadcn-vue, TypeScript, Node built-in test runner

---

### Task 1: Theme mode domain model

**Files:**
- Create: `squirrel-frontend/src/lib/theme.ts`
- Create: `squirrel-frontend/src/lib/theme.test.ts`

**Step 1: Write the failing test**

Create a Node test file for pure theme behavior:

- resolve persisted `light`
- resolve persisted `dark`
- resolve `system` against a provided system preference
- reject unknown persisted values and fall back to `system`
- derive the root dark-state boolean from a selected mode and a system mode

**Step 2: Run test to verify it fails**

Run: `node --test squirrel-frontend/src/lib/theme.test.ts`

Expected: FAIL because `src/lib/theme.ts` does not exist yet.

**Step 3: Write minimal implementation**

Implement pure helpers only:

- `APP_THEME_STORAGE_KEY`
- `type AppThemeMode = 'light' | 'dark' | 'system'`
- `isAppThemeMode`
- `resolveStoredThemeMode`
- `resolveEffectiveTheme`
- `shouldUseDarkTheme`

Keep the module DOM-free so it remains testable with Node only.

**Step 4: Run test to verify it passes**

Run: `node --test squirrel-frontend/src/lib/theme.test.ts`

Expected: PASS.

### Task 2: App theme runtime

**Files:**
- Create: `squirrel-frontend/src/composables/useAppTheme.ts`
- Modify: `squirrel-frontend/src/main.ts`
- Modify: `squirrel-frontend/index.html`

**Step 1: Write the failing test**

Add one more failing pure test in `squirrel-frontend/src/lib/theme.test.ts` covering the startup contract:

- given `mode = system` and `system = dark`, `shouldUseDarkTheme` returns `true`
- given `mode = system` and `system = light`, `shouldUseDarkTheme` returns `false`

This locks the runtime decision before wiring the DOM.

**Step 2: Run test to verify it fails**

Run: `node --test squirrel-frontend/src/lib/theme.test.ts`

Expected: FAIL for the new scenario until the helper behavior is complete.

**Step 3: Write minimal implementation**

Implement `useAppTheme.ts` to:

- read persisted mode
- observe `prefers-color-scheme`
- apply/remove `dark` on `document.documentElement`
- persist explicit user mode changes
- expose `themeMode`, `effectiveTheme`, and `setThemeMode`

Update `main.ts` to initialize app theme before mount.

Remove hard-coded `class="dark"` from `index.html`.

**Step 4: Run test to verify it passes**

Run: `node --test squirrel-frontend/src/lib/theme.test.ts`

Expected: PASS.

### Task 3: Global token rewrite

**Files:**
- Modify: `squirrel-frontend/src/styles/index.css`
- Modify: `squirrel-frontend/tailwind.config.ts`

**Step 1: Write the failing test**

Create a manual regression checklist in the plan and then verify the current code fails it:

- light theme background is not pure white
- dark theme background is not pure black
- primary button is not near-black in light mode
- card and page background are visually separated

There is no CSS test harness in the repo, so the verification for this task is build- and inspection-based.

**Step 2: Run the baseline verification**

Run:

- `rg -n -- "#000\\b|#fff\\b|#ffffff\\b|#000000\\b" squirrel-frontend/src/styles squirrel-frontend/src/components/ui`
- `npm run typecheck`

Expected: token file still reflects grayscale defaults; typecheck should already pass before the rewrite.

**Step 3: Write minimal implementation**

Rewrite the semantic tokens in `index.css` for both `:root` and `.dark`:

- warm canvas light theme
- ink slate dark theme
- cohesive amber-copper primary and ring
- clearer surface hierarchy
- overlay tokens for dialogs and sheets

Adjust `tailwind.config.ts` only if new semantic tokens need supporting names.

**Step 4: Run verification**

Run:

- `npm run typecheck`
- `rg -n -- "#000\\b|#fff\\b|#ffffff\\b|#000000\\b" squirrel-frontend/src/styles squirrel-frontend/src/components/ui`

Expected: typecheck passes; hard-coded pure black/white does not remain in global style primitives except where intentionally media-bound.

### Task 4: Settings theme controls

**Files:**
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Write the failing test**

Add one failing test case in `squirrel-frontend/src/lib/theme.test.ts` for invalid stored values falling back to `system`. This protects the settings control from bad persisted state before wiring the UI.

**Step 2: Run test to verify it fails**

Run: `node --test squirrel-frontend/src/lib/theme.test.ts`

Expected: FAIL until the helper supports that behavior.

**Step 3: Write minimal implementation**

Add an appearance section in settings:

- theme mode segmented control or button group
- `light`, `dark`, `system`
- status copy showing effective mode

Wire it to `useAppTheme`.

Keep the new section aligned with the existing settings layout instead of bolting on a floating control.

**Step 4: Run verification**

Run:

- `node --test squirrel-frontend/src/lib/theme.test.ts`
- `npm run typecheck`

Expected: PASS for both.

### Task 5: High-frequency chrome and overlays

**Files:**
- Modify: `squirrel-frontend/src/App.vue`
- Modify: `squirrel-frontend/src/components/layout/Sidebar.vue`
- Modify: `squirrel-frontend/src/components/layout/SidebarMenuItem.vue`
- Modify: `squirrel-frontend/src/components/layout/GlobalSearchBar.vue`
- Modify: `squirrel-frontend/src/components/ui/button/index.ts`
- Modify: `squirrel-frontend/src/components/ui/card/Card.vue`
- Modify: `squirrel-frontend/src/components/ui/input/Input.vue`
- Modify: `squirrel-frontend/src/components/ui/dialog/DialogContent.vue`
- Modify: `squirrel-frontend/src/components/ui/dialog/DialogScrollContent.vue`
- Modify: `squirrel-frontend/src/components/ui/sheet/SheetContent.vue`
- Modify: `squirrel-frontend/src/components/ui/dropdown-menu/DropdownMenuContent.vue`
- Modify: `squirrel-frontend/src/components/ui/select/SelectContent.vue`

**Step 1: Write the failing test**

Use a static style regression check:

Run:

- `rg -n -- "bg-black/|background:\\s*#000|background:\\s*#fff|#ffffff|#000000" squirrel-frontend/src/components/layout squirrel-frontend/src/components/ui squirrel-frontend/src/App.vue`

Expected: FAIL the intended standard because dialog and sheet overlays still use hard-coded black.

**Step 2: Run the baseline verification**

Run the same command and record the current hits.

**Step 3: Write minimal implementation**

Update high-frequency surfaces to consume semantic tokens:

- stronger sidebar and topbar separation
- calmer hover states
- primary button aligned to the new accent
- cards and inputs with better depth
- overlays using semantic overlay colors instead of direct black alpha values

Do not introduce view-specific one-off palettes.

**Step 4: Run verification**

Run:

- `rg -n -- "bg-black/|background:\\s*#000|background:\\s*#fff|#ffffff|#000000" squirrel-frontend/src/components/layout squirrel-frontend/src/components/ui squirrel-frontend/src/App.vue`
- `npm run build:check`

Expected: hard-coded overlay black is removed from common app chrome; build and typecheck pass.

### Task 6: Settings surface calibration

**Files:**
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Write the failing test**

Use a static check for bright status colors and legacy card layering:

- `rg -n -- "bg-amber-500|bg-blue-500|bg-emerald-500|bg-card/40" squirrel-frontend/src/views/Settings.vue`

Expected: current implementation still uses utility colors and semi-random card layering.

**Step 2: Run the baseline verification**

Run the command above and capture the hits.

**Step 3: Write minimal implementation**

Retune the settings view to the new token system:

- appearance section included
- status pills mapped to semantic color usage or controlled accent/success tokens
- nav and cards use the new surface hierarchy

**Step 4: Run verification**

Run:

- `rg -n -- "bg-amber-500|bg-blue-500|bg-emerald-500|bg-card/40" squirrel-frontend/src/views/Settings.vue`
- `npm run build:check`

Expected: legacy utility color dependence is removed or intentionally minimized; build passes.

### Task 7: Video player theme consolidation

**Files:**
- Modify: `squirrel-frontend/src/components/video-player/themes/variables.css`
- Modify: `squirrel-frontend/src/components/video-player/themes/light.css`
- Modify: `squirrel-frontend/src/components/video-player/themes/dark.css`
- Modify: `squirrel-frontend/src/components/video-player/VideoPlayer.vue`
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Write the failing test**

Use a static regression search:

- `rg -n -- "#000\\b|#fff\\b|#ffffff\\b|#000000\\b|rgba\\(0,\\s*0,\\s*0|rgba\\(255,\\s*255,\\s*255" squirrel-frontend/src/components/video-player squirrel-frontend/src/views/VideoPlay.vue`

Expected: many hits in theme variables and player UI.

**Step 2: Run the baseline verification**

Run the command above and record remaining pure black/white usage.

**Step 3: Write minimal implementation**

Re-author player variables to match the global palette:

- dark theme with ink-slate surfaces and tinted overlays
- light theme with studio-light surfaces and softer contrast
- shared amber-copper emphasis

Keep only truly media-bound black fallbacks in the video surface.

**Step 4: Run verification**

Run:

- `rg -n -- "#000\\b|#fff\\b|#ffffff\\b|#000000\\b|rgba\\(0,\\s*0,\\s*0|rgba\\(255,\\s*255,\\s*255" squirrel-frontend/src/components/video-player squirrel-frontend/src/views/VideoPlay.vue`
- `npm run build:check`

Expected: remaining black/white hits are intentional media fallbacks only; build passes.

### Task 8: Final regression sweep

**Files:**
- Review only

**Step 1: Run targeted checks**

Run:

- `node --test squirrel-frontend/src/lib/theme.test.ts`
- `npm run build:check`
- `rg -n -- "bg-black/|#000\\b|#fff\\b|#ffffff\\b|#000000\\b" squirrel-frontend/src`

**Step 2: Read results**

Confirm:

- theme helper tests pass
- typecheck and build pass
- remaining black/white hits are limited to intentional video media fallback or non-theme assets

**Step 3: Manual spot-check list**

Inspect these screens in both light and dark:

- login
- latest/subscribed list page
- settings
- dialog/sheet/dropdown/select
- video play page

**Step 4: Report actual status**

Summarize what changed, what was verified, and any intentional remaining hard-coded media fallback values.
