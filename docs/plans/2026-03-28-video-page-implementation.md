# Video Page Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the video play page to match the "Immersive Cockpit" terminal aesthetic of the new video list page.

**Architecture:** Use Vue 3 SFC with scoped CSS and CSS variables for theming. Leverage existing composables for data fetching and playback logic. Focus on enhancing the layout and component visuals without breaking core functionality.

**Tech Stack:** Vue 3, Tailwind CSS (for utilities), Iconify, CSS Variables (for glow and theme).

---

### Task 1: Setup Global Terminal Styles
**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Add Terminal Background and Scanning Lines**
- Add `.terminal-viewport` wrapper class to the main container.
- Implement scanline effect using a CSS linear-gradient background on the body or a fixed overlay.

**Step 2: Update Base Colors**
- Set background to `#050505` and ensure text defaults to `rgba(255, 255, 255, 0.8)`.

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/VideoPlay.vue
git commit -m "style: add base terminal background and scanlines"
```

---

### Task 2: Redesign Video Player Container (The Viewfinder)
**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Implement Viewfinder Wrapper**
- Wrap `VideoPlayer` component in a `.viewfinder-box` div.
- Add 12px padding and the 4 corner marks (L-shaped lines).

**Step 2: Style Corner Marks**
- Use absolute positioning for the 4 corners: `1px solid #ff4d00`, `15px x 15px`.
- Add `[MONITOR_ACTIVE]` label at the top center using monospace font.

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/VideoPlay.vue
git commit -m "style: implement viewfinder container with corner marks"
```

---

### Task 3: Redesign Meta Information Panel (The Console)
**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Update Title Section**
- Change title font to bold and add the `[FILE_ENTRY]` prefix.
- Add a subtle 1px orange underline to the title container.

**Step 2: Redesign Channel ID Card**
- Update `.video-channel` to have a "security badge" look.
- Add a CSS-only scanning ring around the channel avatar.
- Style the unsubscribe button as a minimalist wireframe button with glow on hover.

**Step 3: Redesign Action Buttons**
- Update `.video-action` buttons to be `1px solid rgba(255,255,255,0.1)`.
- Implement hover/active states with `#ff4d00` border and `box-shadow` glow.

**Step 4: Commit**
```bash
git add squirrel-frontend/src/views/VideoPlay.vue
git commit -m "style: redesign video meta panel and action buttons"
```

---

### Task 4: Redesign Related Video Sidebar (Data Stream)
**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Implement Indexing Background**
- Add a large, low-opacity (5%) index number (01, 02, etc.) behind each `related-video-card`.

**Step 2: Update Card Visuals**
- Remove card rounded corners (max 2px).
- Change metadata font to monospace, size `0.65rem`.

**Step 3: Add Hover "Data Reading" Effect**
- Add a transition that shows `[DATA_READING]` text overlay on the thumbnail when hovering.

**Step 4: Commit**
```bash
git add squirrel-frontend/src/views/VideoPlay.vue
git commit -m "style: redesign related video sidebar with indexing"
```

---

### Task 5: Final Polishing and Transitions
**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Refine Transitions**
- Update `<transition name="fade">` and `channel-dismiss` to have a slightly more "digital" feel (sharper timings or subtle vertical slide).

**Step 2: Fix Responsive Issues**
- Ensure the viewfinder and console look good on mobile, adjusting padding and font sizes.

**Step 3: Verify and Commit**
- Run a build check: `npm run build` in `squirrel-frontend`.
```bash
git add squirrel-frontend/src/views/VideoPlay.vue
git commit -m "style: final polish and responsive adjustments for video page"
```
