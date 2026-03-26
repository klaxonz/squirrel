# Video Card Meta Spacing Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Reduce the vertical spacing between the video title and the channel metadata on all shared video cards.

**Architecture:** Make a single shared stylesheet change in the reusable video card CSS. Avoid changing component structure or typography so the behavior stays stable and the visual change remains narrow.

**Tech Stack:** Vue 3, shared component CSS, Vite

---

### Task 1: Tighten the shared card text rhythm

**Files:**
- Modify: `squirrel-frontend/src/styles/components/video-card.css`

**Step 1: Identify the controlling spacing rule**

Check the shared video card stylesheet for the block that controls the gap between:
- `.video-title`
- `.video-card__meta-row`

Expected finding:
- the metadata row uses a positive top margin that creates the visible gap

**Step 2: Reduce the gap minimally**

Update the spacing rule with a smaller value.

Do not change:
- title font size
- line clamp
- metadata font size
- card min-height

**Step 3: Verify**

Run: `npm run build:check`

Expected:
- `vue-tsc --noEmit` passes
- `vite build` passes
