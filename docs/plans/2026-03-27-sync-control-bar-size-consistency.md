# Sync Control Bar Size Consistency Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make the sync center action controls use one consistent visual size system.

**Architecture:** Keep the change local to the sync control bar. Adjust only the classes applied to the header controls so the tabs, toggle shell, buttons, and timestamp pill share the same height and text scale without changing shared primitives.

**Tech Stack:** Vue 3, Vite, Tailwind utilities, local scoped component styling

---

### Task 1: Normalize the action control sizes

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncControlBar.vue`

**Step 1: Identify the mismatched controls**

Check the current classes for:
- `TabsList`
- `TabsTrigger`
- auto-refresh label wrapper
- action buttons
- update badge

Expected finding:
- buttons use a smaller size token than tabs and the toggle shell

**Step 2: Apply one shared size target**

Update the action row so:
- buttons use the default button size
- tabs use explicit height and text size classes
- the toggle shell uses the same visible height and padding
- the update badge uses the same height and text size

**Step 3: Keep behavior unchanged**

Do not change:
- emitted events
- labels and copy
- responsive wrap behavior

**Step 4: Verify with a production-safe frontend check**

Run: `npm run build:check`

Expected:
- `vue-tsc --noEmit` passes
- `vite build` passes

**Step 5: Review visually**

Confirm the right-side control group no longer looks mixed in height or density.
