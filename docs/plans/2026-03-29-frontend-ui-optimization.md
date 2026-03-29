# Cyber-Sync Tactical Terminal Frontend Optimization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the Sync Center, Video Feed, and Plugin Manager into a cohesive "Cyber-Sync Tactical Terminal" aesthetic.

**Architecture:** 
- Enhance existing Vue components with scoped CSS for "Tactical" effects.
- Use Tailwind CSS for layout and custom CSS for neon, pulse, and matrix effects.
- Standardize technical typography with `JetBrains Mono`.

**Tech Stack:** Vue 3, Tailwind CSS, Lucide Icons, JetBrains Mono.

---

### Task 1: Optimize VideoItem.vue with Backlight Glow and Minimalist Overlay

**Files:**
- Modify: `squirrel-frontend/src/components/feed/VideoItem.vue`

**Step 1: Update Template for Tactical Overlays**
Add scanline and status overlay elements.

```vue
<div class="video-viewer-frame">
  <!-- ... existing img ... -->
  <div class="scanline"></div>
  <div class="video-status-overlay">
    <div class="flex justify-between items-start w-full">
      <div class="tech-tag">[SIGNAL_LOCKED]</div>
      <div v-if="isLikedVideo" class="fav-dot"></div>
    </div>
    <div class="flex justify-between items-end w-full">
      <div class="tech-tag">ID: {{ videoCardId }}</div>
      <div class="tech-time">{{ formatDuration(video.duration) }}</div>
    </div>
  </div>
  <!-- ... existing progress bar ... -->
</div>
```

**Step 2: Update Styles for Backlight and Hover Effects**
Refine the hover state with neon glow and scanline animation.

```css
<style scoped>
.video-terminal-item:hover .video-viewer-frame {
  border-color: rgba(255, 77, 0, 0.4);
  box-shadow: 
    0 0 30px rgba(255, 77, 0, 0.15),
    inset 0 0 15px rgba(255, 77, 0, 0.05);
}

.scanline {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.1);
  box-shadow: 0 0 10px rgba(255, 255, 255, 0.2);
  z-index: 3;
  opacity: 0;
  pointer-events: none;
}

.video-terminal-item:hover .scanline {
  animation: scan 2s linear infinite;
  opacity: 1;
}

.video-status-overlay {
  position: absolute;
  inset: 0;
  padding: 0.75rem;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  z-index: 4;
  background: linear-gradient(to bottom, rgba(0,0,0,0.4) 0%, transparent 30%, transparent 70%, rgba(0,0,0,0.6) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
  pointer-events: none;
}

.video-terminal-item:hover .video-status-overlay {
  opacity: 1;
}

.tech-tag {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.5rem;
  color: #ff4d00;
  letter-spacing: 0.1em;
  opacity: 0.8;
}

@keyframes scan {
  0% { top: 0; }
  100% { top: 100%; }
}
</style>
```

**Step 3: Commit**
```bash
git add squirrel-frontend/src/components/feed/VideoItem.vue
git commit -m "feat(ui): add tactical overlays and backlight glow to VideoItem"
```

---

### Task 2: Refactor SyncCenter.vue into a Signal Monitoring Dashboard

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncControlBar.vue`

**Step 1: Add Matrix Background and Tactical Layout**
Update `SyncCenter.vue` with a pixel-dot background and refined spacing.

```vue
<template>
  <div class="sync-center-page tactical-terminal min-h-full">
    <div class="matrix-bg"></div>
    <div class="toolbar-container py-8 relative z-10">
      <!-- ... -->
    </div>
  </div>
</template>

<style scoped>
.tactical-terminal {
  background-color: #050505;
  position: relative;
  overflow: hidden;
}

.matrix-bg {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 20px 20px;
  pointer-events: none;
}
</style>
```

**Step 2: Update SyncControlBar for Bracketed Actions**
Modify buttons to use `[ ACTION ]` format and `JetBrains Mono`.

```vue
<button class="tactical-btn">
  [ {{ refreshing ? 'REFRESHING...' : 'REFRESH_ALL' }} ]
</button>
```

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/SyncCenter.vue squirrel-frontend/src/components/sync-center/SyncControlBar.vue
git commit -m "feat(ui): implement tactical dashboard style for SyncCenter"
```

---

### Task 3: Re-imagine PluginManager.vue as a Hardware Rack

**Files:**
- Modify: `squirrel-frontend/src/views/PluginManager.vue`

**Step 1: Replace Table with Rack Mount Cards**
Refactor the plugin list into a vertical stack of modular cards.

```vue
<div class="plugin-rack space-y-4">
  <div v-for="plugin in displayPlugins" :key="plugin.plugin_id" class="rack-unit">
    <div class="unit-handle"></div>
    <div class="unit-content">
      <div class="flex items-center gap-4">
        <div class="led-indicator" :class="getLedClass(plugin)"></div>
        <div class="flex-1">
          <div class="unit-title">{{ plugin.display_name }}</div>
          <div class="unit-id">{{ plugin.plugin_id }} v{{ plugin.version }}</div>
        </div>
        <!-- Actions -->
      </div>
    </div>
    <div class="unit-vents"></div>
  </div>
</div>
```

**Step 2: Add LED and Hardware Styles**
Implement the rack mount aesthetic with CSS.

```css
<style scoped>
.rack-unit {
  background: rgba(255, 255, 255, 0.02);
  border: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  height: 80px;
  position: relative;
}

.unit-handle {
  width: 4px;
  background: #ff4d00;
  opacity: 0.3;
}

.led-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  box-shadow: 0 0 10px currentColor;
}

.led-running { color: #10b981; animation: pulse 2s infinite; }
.led-failed { color: #ef4444; animation: flash 0.5s infinite; }

.unit-id {
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  opacity: 0.4;
}

@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>
```

**Step 3: Commit**
```bash
git add squirrel-frontend/src/views/PluginManager.vue
git commit -m "feat(ui): refactor PluginManager into a hardware rack mount UI"
```

---

### Task 4: Final Verification and Polish

**Step 1: Run Type Check**
Run: `npm run typecheck` in `squirrel-frontend`
Expected: PASS

**Step 2: Verify Visuals**
Check all three optimized modules in the browser for visual consistency and smooth animations.
