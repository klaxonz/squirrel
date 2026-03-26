# Video Play Actions Inline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Inline all video actions and reduce their button size on the play page.

**Architecture:** Keep the current action computation and click handlers. Only change how actions are rendered in the `VideoPlay.vue` template and compact the related CSS styles.

**Tech Stack:** Vue 3, Vite, scoped CSS in SFC

---

### Task 1: Flatten the action area

**Files:**
- Modify: `squirrel-frontend/src/views/VideoPlay.vue`

**Step 1: Remove the overflow menu trigger**
- Delete the `更多` button and popup markup from the video metadata action row.

**Step 2: Render all actions inline**
- Render both primary and overflow actions through the same inline button pattern.
- Keep existing labels, icons, and click behavior.

**Step 3: Compact action button styling**
- Reduce action button min-height, horizontal padding, icon size, and label font size.
- Keep wrapping behavior so the row remains stable on narrow widths.

**Step 4: Verify**
- Run: `npm run typecheck`
- Expected: PASS
