# Neon Pulse Sidebar Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Optimize the sidebar UI and UX with a "Neon Pulse" aesthetic, featuring icon support, section headers, and refined animations.

**Architecture:** 
- Enhance `SidebarMenuItem.vue` to render icons and apply advanced CSS transitions.
- Update `Sidebar.vue` to group menu items with visual headers.
- Use Tailwind CSS for layout and custom CSS for "neon" effects.

**Tech Stack:** Vue 3, Tailwind CSS, Heroicons.

---

### Task 1: Update SidebarMenuItem.vue for Icon Support and Neon Pulse Styles

**Files:**
- Modify: `squirrel-frontend/src/components/layout/SidebarMenuItem.vue`

**Step 1: Update Template to Include Icon**
Add the icon component to the template.

```vue
<template>
  <router-link
    :to="item.path"
    class="menu-item-neon"
    :class="{ 'is-active': isActive }"
  >
    <div class="menu-item-content">
      <div class="icon-wrapper">
        <component :is="item.icon" class="menu-icon" />
      </div>
      <div class="label-wrapper">
        <span class="menu-index">{{ index < 10 ? '0' + index : index }}</span>
        <span class="menu-label">{{ item.name }}</span>
      </div>
    </div>
    <div class="menu-active-glow"></div>
  </router-link>
</template>
```

**Step 2: Update Styles for Neon Pulse Effect**
Replace existing styles with the new "Neon Pulse" CSS.

```css
<style scoped>
.menu-item-neon {
  position: relative;
  display: flex;
  padding: 1.25rem 1rem;
  color: rgba(255, 255, 255, 0.3);
  text-decoration: none;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  border-bottom: 1px solid rgba(255, 255, 255, 0.02);
  overflow: hidden;
}

.menu-item-neon:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.02);
}

.menu-item-neon:hover .menu-icon {
  transform: translateX(2px);
  color: #fff;
}

.is-active {
  color: #fff;
  background: linear-gradient(90deg, rgba(255, 77, 0, 0.05) 0%, transparent 100%);
}

.menu-item-content {
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 2;
}

.icon-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 1.5rem;
  height: 1.5rem;
}

.menu-icon {
  width: 1.25rem;
  height: 1.25rem;
  transition: all 0.3s ease;
}

.is-active .menu-icon {
  color: #ff4d00;
  filter: drop-shadow(0 0 5px rgba(255, 77, 0, 0.8));
  animation: pulse 2s infinite ease-in-out;
}

.label-wrapper {
  display: flex;
  flex-direction: column;
}

.menu-index {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  letter-spacing: 0.1em;
  opacity: 0.4;
  margin-bottom: -0.1rem;
}

.menu-label {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.menu-active-glow {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 2px;
  background: #ff4d00;
  opacity: 0;
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
  box-shadow: 0 0 15px #ff4d00;
}

.is-active .menu-active-glow {
  opacity: 1;
  height: 100%;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.7; transform: scale(1.05); }
}
</style>
```

**Step 3: Commit**

```bash
git add squirrel-frontend/src/components/layout/SidebarMenuItem.vue
git commit -m "feat(ui): implement Neon Pulse styles for SidebarMenuItem"
```

---

### Task 2: Update Sidebar.vue with Group Headers and Refined Layout

**Files:**
- Modify: `squirrel-frontend/src/components/layout/Sidebar.vue`

**Step 1: Update Template to Include Group Headers**
Add visual headers for each `NAV_GROUPS`.

```vue
<nav class="sidebar-nav-neon flex-1 overflow-y-auto py-4 scrollbar-hide">
  <div
    v-for="(group, groupIdx) in NAV_GROUPS"
    :key="group.key"
    class="sidebar-section-neon mb-6"
  >
    <div class="section-header-neon">
      <span class="section-title">{{ group.label }}</span>
      <div class="section-line"></div>
    </div>
    <SidebarMenuItem
      v-for="(item, itemIdx) in group.items"
      :key="item.path"
      :item="item"
      :index="(groupIdx * 3) + itemIdx + 1"
      :is-active="isNavigationItemActive(item, $route.path)"
    />
  </div>
</nav>
```

**Step 2: Update Sidebar Styles**
Refine the sidebar width and header/footer styles.

```css
<style scoped>
.sidebar-minimal {
  width: var(--sidebar-width, 11rem); /* Increased width for icons and labels */
  background: #050505;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
}

.sidebar-header-minimal {
  padding: 2rem 1.25rem;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.section-header-neon {
  padding: 0 1rem 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.section-title {
  font-size: 0.55rem;
  font-weight: 700;
  letter-spacing: 0.2em;
  color: rgba(255, 255, 255, 0.15);
  text-transform: uppercase;
  white-space: nowrap;
}

.section-line {
  height: 1px;
  flex: 1;
  background: rgba(255, 255, 255, 0.03);
}

/* ... existing footer styles with minor tweaks ... */
</style>
```

**Step 3: Commit**

```bash
git add squirrel-frontend/src/components/layout/Sidebar.vue
git commit -m "feat(ui): add group headers and refine Sidebar layout"
```

---

### Task 3: Final Polish and Verification

**Step 1: Verify Visuals**
Check the sidebar in the browser to ensure:
1. Icons are rendered correctly.
2. Active state has the neon glow and pulse animation.
3. Group headers are visible and well-spaced.
4. Hover effects are smooth.

**Step 2: Run Build Check**
Ensure no type errors were introduced.

Run: `npm run typecheck` in `squirrel-frontend`
Expected: PASS
