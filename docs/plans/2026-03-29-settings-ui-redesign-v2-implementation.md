# Settings UI Redesign V2 - The Precision Console Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the settings page with a minimalist, typography-driven, non-card layout titled "The Precision Console".

**Architecture:** 
- Remove all card containers and background blocks.
- Use 1px borders and negative space for structure.
- Implement kinetic hover effects (line growth, text shift).
- Implement staggered reveal animations (delay per row).

**Tech Stack:** Vue 3, Tailwind CSS, Lucide Icons, Vue TransitionGroup.

---

### Task 1: Refactor Settings.vue Skeleton & Sidebar

**Files:**
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Clean up existing card-based styles**
- Remove `.theme-card`, `.setting-item` (old), and card-specific utility classes.
- Update `.content-container` to have maximum negative space.

**Step 2: Implement Typography-driven Sidebar**
- Update sidebar navigation to be text-only with a vertical indicator line.
- Add `scaleY` transition for the active indicator.

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/Settings.vue
git commit -m "style: refactor settings skeleton and text-only sidebar"
```

### Task 2: Implement Kinetic Setting Rows

**Files:**
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Create the Kinetic Row Component/Structure**
- Use `group` class on each setting row.
- Add two absolute 1px lines (top and bottom) that scale from the center on hover.
- Add `translate-x` transition to the title text.

**Step 2: Apply to Appearance, Content, Playback, and System tabs**
- Update all setting items to use the new kinetic structure.
- Ensure the layout is `Label + Desc (Left)` and `Control (Right)`.

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/Settings.vue
git commit -m "style: implement kinetic setting rows with line growth and text shift"
```

### Task 3: Implement Staggered Reveal System

**Files:**
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Add TransitionGroup for List Animation**
- Wrap setting lists in `<TransitionGroup name="staggered-reveal">`.
- Use a dynamic `--delay` CSS variable based on the item's index.

**Step 2: Define Shutter Animation in CSS**
- Add `@keyframes staggered-reveal` with `rotateX(5deg)`, `translateY(10px)`, and `opacity: 0`.
- Ensure smooth `cubic-bezier` timing.

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/Settings.vue
git commit -m "style: add staggered reveal and 3D shutter animation for settings"
```

### Task 4: Redesign SiteConfigSection (Drafting Table Style)

**Files:**
- Modify: `squirrel-frontend/src/components/settings/SiteConfigSection.vue`

**Step 1: Update Header & Grid Structure**
- Use the same large typography for the header.
- Change the site grid to use thin vertical/horizontal lines instead of cards.

**Step 2: Refine Site Items**
- Remove background colors and shadows.
- Add minimal hover effects (border brightening, icon rotation).

**Step 3: Commit**
```bash
git add squirrel-frontend/src/components/settings/SiteConfigSection.vue
git commit -m "style: redesign site config section in drafting table style"
```
