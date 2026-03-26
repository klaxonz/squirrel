# Video Play Decard Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove the floating card treatment from the video player page while preserving layout clarity.

**Architecture:** Keep the existing DOM structure and interaction logic. Restrict the change to presentation updates in the play page stylesheet so the page shifts from stacked panels to a flatter content layout.

**Tech Stack:** Vue 3, Vite, scoped CSS in SFC

---

### Task 1: Flatten the major page sections

**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Remove the shell styling from the player section**
- Delete the border, rounded corners, background fill, and shadow from `.video-section`.

**Step 2: Remove the shell styling from the metadata section**
- Delete the border, rounded corners, gradient background, and shadow from `.video-meta__panel`.
- Keep spacing and the existing internal divider on `.video-meta__actions`.

**Step 3: Remove the shell styling from the related videos panel**
- Delete the border, rounded corners, gradient background, and shadow from `.video-aside__panel`.
- Keep title spacing so the aside still reads as a section.

**Step 4: Soften related item card treatment**
- Reduce border, background, radius, and hover elevation on `.related-video-card`.
- Keep clickable affordance without a raised-card look.

**Step 5: Verify**
- Run: `npm run typecheck`
- Expected: PASS
