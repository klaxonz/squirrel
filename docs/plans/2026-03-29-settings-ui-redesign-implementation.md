# Settings Page UI/UX Redesign Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Redesign the settings page with a refined minimalist aesthetic, matching the project's "pro" look.

**Architecture:**
- Update `Settings.vue` to use a more refined layout and styling.
- Update `SiteConfigSection.vue` for a cleaner site configuration grid.
- Use Tailwind CSS for all styling, adhering to existing design tokens.
- Enhance interactions with smooth transitions and hover states.

**Tech Stack:** Vue 3, Tailwind CSS, Lucide Icons, Shadcn/UI (Switch).

---

### Task 1: Refactor `Settings.vue` Layout & Sidebar

**Files:**
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Update Sidebar Styles**
- Refine the sidebar navigation with better active and hover states.
- Use the project's orange (`primary`) for the active indicator.
- Add subtle background highlights on hover.

**Step 2: Update Main Content Header**
- Make the header more prominent with a bold title and secondary description.

**Step 3: Update Setting Item Rows**
- Create a consistent layout for setting items: Label + Description on the left, Control on the right.
- Add a subtle hover effect to each row.

**Step 4: Commit**
```bash
git add squirrel-frontend/src/views/Settings.vue
git commit -m "style: redesign settings page layout and sidebar"
```

### Task 2: Redesign Appearance Tab (Theme Selection)

**Files:**
- Modify: `squirrel-frontend/src/views/Settings.vue`

**Step 1: Update Theme Selection Cards**
- Redesign the `theme-card` with a cleaner look.
- Use better icons and a clear "active" state indicator (e.g., a subtle border or glow).
- Improve the grid layout for theme options.

**Step 2: Commit**
```bash
git add squirrel-frontend/src/views/Settings.vue
git commit -m "style: redesign theme selection cards in appearance tab"
```

### Task 3: Redesign Site Config Section

**Files:**
- Modify: `squirrel-frontend/src/components/settings/SiteConfigSection.vue`

**Step 1: Update Site Card Styles**
- Make the site cards more compact and visually refined.
- Use a subtle background and border.
- Refine the status indicator dot (e.g., add a subtle glow when enabled).

**Step 2: Improve Site Grid Layout**
- Ensure the grid is responsive and well-spaced.

**Step 3: Commit**
```bash
git add squirrel-frontend/src/components/settings/SiteConfigSection.vue
git commit -m "style: redesign site configuration section"
```

### Task 4: Final Polish & Verification

**Step 1: Verify Transitions**
- Ensure the "slide-up" animation works smoothly when switching tabs.
- Check all hover states for consistency.

**Step 2: Verify Responsiveness**
- Check the layout on different screen sizes (especially the sidebar and site grid).

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/Settings.vue squirrel-frontend/src/components/settings/SiteConfigSection.vue
git commit -m "style: final polish for settings page redesign"
```
