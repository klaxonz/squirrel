# Video Play Theater Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the video playback page switch into a YouTube-like theater mode where the player widens and related videos move below the player instead of disappearing.

**Architecture:** Keep `VideoPlayer.vue` unchanged as the source of the `widescreenChange` event and confine all theater-mode work to `VideoPlay.vue`. Use one markup path for the related-video section, remove the widescreen-only hide branch, and let the page container swap between desktop two-column and widescreen single-column grid rules.

**Tech Stack:** Vue 3 SFC, scoped CSS, Vite, Node `node:test`

---

## File Structure

- Modify: `squirrel-frontend/src/views/VideoPlay.vue`
  Owns the `isWidescreen` state, the player/meta/related page structure, and all layout CSS that controls desktop rail mode versus theater mode.
- Create: `squirrel-frontend/test/video-play-theater-mode.test.mjs`
  Source-level regression checks that lock the no-duplicate-markup layout contract, the removal of the widescreen `hidden` branch, and the CSS rules that convert the page from rail mode to theater mode.

## Task 1: Add A Failing Theater-Mode Regression Test

**Files:**
- Create: `squirrel-frontend/test/video-play-theater-mode.test.mjs`
- Test: `squirrel-frontend/src/views/VideoPlay.vue`

- [ ] **Step 1: Write the failing test**

```javascript
import assert from 'node:assert/strict'
import test from 'node:test'
import { readFile } from 'node:fs/promises'

const videoPlayPath = new URL('../src/views/VideoPlay.vue', import.meta.url)

test('video play theater mode keeps the related rail mounted and switches layout through container classes', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(
    source,
    /<div :class="\['video-page__container', \{ 'is-widescreen': isWidescreen \}\]">/,
  )
  assert.match(source, /<div class="video-aside">/)
  assert.doesNotMatch(source, /isWidescreen \? 'hidden' : ''/)
})

test('video play theater mode defines a single-column widescreen layout and disables the sidebar rail behavior', async () => {
  const source = await readFile(videoPlayPath, 'utf8')

  assert.match(source, /\.video-page__container\.is-widescreen\s*\{/)
  assert.match(source, /grid-template-columns:\s*minmax\(0,\s*1fr\);/)
  assert.match(source, /\.video-page__container\.is-widescreen\s+\.video-aside\s*\{/)
  assert.match(source, /position:\s*static;/)
  assert.match(source, /\.video-page__container\.is-widescreen\s+\.related-video-card\s*\{/)
})
```

- [ ] **Step 2: Run test to verify it fails**

Run from `squirrel-frontend`:

```bash
node --test test/video-play-theater-mode.test.mjs
```

Expected: FAIL because `VideoPlay.vue` still renders the aside with `isWidescreen ? 'hidden' : ''` and does not yet define the dedicated `.video-page__container.is-widescreen` layout rules.

- [ ] **Step 3: Commit the failing test**

```bash
git add squirrel-frontend/test/video-play-theater-mode.test.mjs
git commit -m "test: add theater mode layout regression"
```

## Task 2: Keep The Related Section Mounted And Switch Layout Through Container State

**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`
- Test: `squirrel-frontend/test/video-play-theater-mode.test.mjs`

- [ ] **Step 1: Update the page container and aside markup**

Replace the current container and aside bindings with this target structure:

```vue
<template>
  <div
    ref="videoPageRef"
    class="video-page terminal-viewport scrollbar-hide"
    :class="{ 'is-widescreen': isWidescreen }"
  >
    <div :class="['video-page__container', { 'is-widescreen': isWidescreen }]">
      <div class="video-main">
        <div ref="videoSectionRef" class="video-section">
          <div class="video-container">
            <Transition name="fade-player" appear>
              <div class="viewfinder-box">
                <div class="viewfinder-corner viewfinder-corner--top-left"></div>
                <div class="viewfinder-corner viewfinder-corner--top-right"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-left"></div>
                <div class="viewfinder-corner viewfinder-corner--bottom-right"></div>
                <VideoPlayer
                  ref="videoPlayerRef"
                  v-if="video"
                  :source="playbackSource"
                  :subtitles="subtitleTracks"
                  :poster="video?.thumbnail"
                  :title="video?.title"
                  :initialTime="startTime"
                  :has-prev="hasPrevVideo"
                  :has-next="hasNextVideo"
                  :external-error="externalError"
                  :widescreen="isWidescreen"
                  :adapter="playerAdapter"
                  :theme="effectiveTheme"
                  :i18n-options="{ persist: true, storageKey: 'sp-locale', applyToDocument: true, useGlobal: true }"
                  :enable-global-shortcuts="true"
                  :enable-click-outside-close-menu="true"
                  :enable-window-resize="true"
                  @play="onVideoPlay"
                  @pause="onVideoPause"
                  @ended="handleAutoplayNext"
                  @timeupdate="onVideoTimeUpdate"
                  @prev="handlePrevVideo"
                  @next="handleNextVideo"
                  @widescreenChange="toggleWidescreen"
                  @retry="handlePlayerRetry"
                />
              </div>
            </Transition>
          </div>
        </div>

        <div ref="videoMetaRef" class="video-meta">
          <!-- keep the existing metadata block unchanged -->
        </div>
      </div>

      <div class="video-aside">
        <div class="video-aside__panel">
          <!-- keep the existing related video list markup unchanged -->
        </div>
      </div>
    </div>
  </div>
</template>
```

Keep `toggleWidescreen`, `setWidescreenClass`, and `syncWidescreenSidebarState` unchanged. This task is only about removing the widescreen-only hide branch and making container state the layout source of truth.

- [ ] **Step 2: Run the regression test to confirm the markup portion passes and the CSS assertions still fail**

Run from `squirrel-frontend`:

```bash
node --test test/video-play-theater-mode.test.mjs
```

Expected: still FAIL, but now only on the CSS assertions because the template no longer hides `.video-aside` in widescreen mode.

- [ ] **Step 3: Commit the template refactor**

```bash
git add squirrel-frontend/src/views/VideoPlay.vue
git commit -m "refactor(video-play): keep related rail mounted in widescreen"
```

## Task 3: Consolidate Layout CSS And Implement Theater Mode Grid Rules

**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`
- Test: `squirrel-frontend/test/video-play-theater-mode.test.mjs`

- [ ] **Step 1: Replace the duplicated layout blocks with one canonical theater-mode layout section**

In `squirrel-frontend/src/views/VideoPlay.vue`, remove the repeated definitions for:

- `.video-page__container`
- `.video-main`
- `.video-section`
- `.video-container`
- `.viewfinder-box`
- `.video-meta`
- `.video-aside`
- `.related-video-card`

Replace them with this canonical layout block:

```css
.video-page {
  min-height: 100%;
}

.video-page__container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  width: 100%;
  max-width: 1720px;
  margin: 0 auto;
  padding: 1rem;
}

.video-main {
  width: 100%;
  min-width: 0;
}

.video-section {
  position: relative;
  width: 100%;
  margin: 0 auto;
  overflow: hidden;
  background: transparent;
  border: none;
  border-radius: 0;
  box-shadow: none;
}

.video-container {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: #000;
  border-radius: 0;
}

.viewfinder-box {
  position: relative;
  width: 100%;
  height: 100%;
  padding: 12px;
  display: flex;
  flex-direction: column;
}

.video-container :deep(.sp-player) {
  background: hsl(var(--background));
  border-radius: 0;
  overflow: hidden;
}

.video-meta {
  margin-top: 0.875rem;
  padding: 0 12px;
}

.video-aside {
  width: 100%;
  min-width: 0;
}

.related-videos-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.related-video-card {
  position: relative;
  display: grid;
  grid-template-columns: 110px 1fr;
  gap: 0.6rem;
  padding: 0.25rem;
  align-items: flex-start;
  border-radius: 3px;
  background: rgba(255, 255, 255, 0.015);
  border: 1px solid rgba(255, 255, 255, 0.03);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.2, 0, 0.1, 1);
}

@media (min-width: 1280px) {
  .video-page__container {
    display: grid;
    grid-template-columns: minmax(0, 1fr) 400px;
    align-items: start;
    column-gap: 1.5rem;
    padding: 1.5rem 2rem 2rem;
  }

  .video-aside {
    position: sticky;
    top: 1.5rem;
  }

  .video-page__container.is-widescreen {
    grid-template-columns: minmax(0, 1fr);
    max-width: min(1920px, calc(100vw - 2rem));
  }

  .video-page__container.is-widescreen .video-aside {
    position: static;
    top: auto;
    margin-top: 0.5rem;
  }

  .video-page__container.is-widescreen .related-video-card {
    grid-template-columns: 180px minmax(0, 1fr);
    gap: 0.8rem;
    padding: 0.45rem 0;
  }
}

@media (min-width: 640px) and (max-width: 1279px) {
  .related-video-card {
    grid-template-columns: 140px 1fr;
    gap: 0.8rem;
    padding: 0.35rem;
  }
}

@media (max-width: 640px) {
  .viewfinder-box {
    padding: 6px;
  }

  .video-meta {
    padding: 0 6px;
  }
}

@supports not (aspect-ratio: 1 / 1) {
  .video-container {
    height: 0;
    padding-bottom: 56.25%;
  }
}
```

Keep the existing decorative rules for corners, card overlays, typography, and transitions. Only deduplicate the layout primitives that currently override each other.

- [ ] **Step 2: Run the theater-mode regression test to verify it passes**

Run from `squirrel-frontend`:

```bash
node --test test/video-play-theater-mode.test.mjs
```

Expected: PASS with `2 passed`.

- [ ] **Step 3: Commit the theater-mode layout rules**

```bash
git add squirrel-frontend/src/views/VideoPlay.vue squirrel-frontend/test/video-play-theater-mode.test.mjs
git commit -m "feat(video-play): add theater mode layout"
```

## Task 4: Run Verification And Manual Theater-Mode Checks

**Files:**
- Modify: `squirrel-frontend/test/video-play-theater-mode.test.mjs`
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

- [ ] **Step 1: Run the targeted source regression test**

Run from `squirrel-frontend`:

```bash
node --test test/video-play-theater-mode.test.mjs
```

Expected: PASS with `2 passed`.

- [ ] **Step 2: Run frontend typecheck**

Run from `squirrel-frontend`:

```bash
npm run typecheck
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 3: Run frontend build verification**

Run from `squirrel-frontend`:

```bash
npm run build:check
```

Expected: PASS with both typecheck and production build succeeding.

- [ ] **Step 4: Perform manual theater-mode verification**

1. Open a video page at desktop width.
2. Confirm normal mode shows the player and metadata on the left and related videos on the right.
3. Click the player widescreen button.
4. Confirm the player becomes visibly wider.
5. Confirm the metadata remains directly below the player.
6. Confirm related videos move below the metadata instead of disappearing.
7. Resize to a narrow viewport and confirm the page remains single-column without duplicate related-video markup.
8. Exit widescreen and confirm the related section returns to the right rail on desktop width.

- [ ] **Step 5: Commit final verification-only adjustments if needed**

```bash
git add squirrel-frontend/src/views/VideoPlay.vue squirrel-frontend/test/video-play-theater-mode.test.mjs
git commit -m "test(video-play): tighten theater mode regression coverage"
```

## Self-Review

### Spec coverage

- Widening the player area through page-level grid rules is covered by Task 3.
- Keeping metadata below the player in both modes is preserved by Task 2 and Task 3.
- Moving related videos below the player instead of hiding them is covered by Task 2 and verified by Task 1 and Task 4.
- Avoiding `VideoPlayer.vue` changes is enforced by the file structure and task scope.
- Cleaning up repeated layout selectors in `VideoPlay.vue` is covered by Task 3.

### Placeholder scan

- No `TODO`, `TBD`, or deferred implementation notes remain.
- Every code-changing step includes concrete code snippets, file paths, commands, and expected outcomes.

### Type consistency

- The page state remains `isWidescreen`.
- The page container modifier remains `.video-page__container.is-widescreen`.
- The related section stays `.video-aside`.
- The regression test path remains `squirrel-frontend/test/video-play-theater-mode.test.mjs`.
