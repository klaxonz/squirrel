# 丝滑科幻风无边界流水线 (Fluid Sci-Fi Pipeline) 重构计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 彻底移除“卡片”容器，建立基于垂直能量导轨的无边界布局，实现激光扫描悬浮效、流体波形进度条及丝滑的任务流转动效。

---

### Task 12: 定义“丝滑科幻”全局动效与颜色 (Global Aesthetics)

**Files:**
- Modify: `squirrel-frontend/src/styles/index.css`

- [ ] **Step 1: 引入 OKLCH 颜色与激光扫描动画**

```css
:root {
  --sci-fi-cyan: oklch(75% 0.15 200);
  --sci-fi-amber: oklch(75% 0.15 60);
  --sci-fi-orange: oklch(70% 0.2 40);
  --sci-fi-green: oklch(75% 0.2 150);
}

@keyframes laser-scan {
  0% { transform: translateX(-100%) skewX(-20deg); opacity: 0; }
  20% { opacity: 0.5; }
  80% { opacity: 0.5; }
  100% { transform: translateX(200%) skewX(-20deg); opacity: 0; }
}

.animate-scan {
  position: relative;
  overflow: hidden;
}

.animate-scan::after {
  content: "";
  position: absolute;
  inset: 0;
  width: 40px;
  background: linear-gradient(90deg, transparent, var(--sci-fi-orange), transparent);
  filter: blur(8px);
  opacity: 0;
  pointer-events: none;
}

.animate-scan:hover::after {
  animation: laser-scan 0.8s ease-in-out;
}
```

---

### Task 13: 布局重构：建立无边界导轨 (Borderless Layout)

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

- [ ] **Step 1: 移除 Grid 容器，添加背景编号与垂直导轨**
- 移除 `flow-shell` 的 grid 间距和列背景。
- 在三栏之间添加绝对定位的垂直线 (`w-px bg-white/5 shadow-[0_0_10px_rgba(255,255,255,0.05)]`)。
- 在每一栏的背景层添加巨型数字 (01, 02, 03)。

---

### Task 14: 重绘数据项：去容器与扫描交互 (Data Items)

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncQueueBoard.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncActiveRunBoard.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncRecentRunBoard.vue`

- [ ] **Step 1: 移除所有 Board Shell 和 Row 的背景/边框**
- [ ] **Step 2: 应用 `animate-scan` 类和悬浮位移**
- 鼠标悬浮时，内容整体右移 `translate-x-1`，背景呈现极淡的 `bg-white/[0.02]`。

---

### Task 15: 实现流体波形进度条 (Fluid Progress)

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncActiveRunBoard.vue`

- [ ] **Step 1: 将方块进度条替换为流体线条**

```vue
<div class="relative h-1 w-full bg-white/5 mt-3 overflow-hidden">
  <div 
    class="absolute inset-y-0 left-0 bg-gradient-to-r from-transparent via-[--sci-fi-orange] to-transparent transition-all duration-500 shadow-[0_0_15px_var(--sci-fi-orange)]"
    :style="{ width: (item.progress_percent || 0) + '%', opacity: 0.8 }"
  ></div>
  <!-- 动态波纹层 -->
  <div class="absolute inset-0 opacity-30 animate-pulse bg-[--sci-fi-orange]" :style="{ width: (item.progress_percent || 0) + '%' }"></div>
</div>
```

---

### Task 16: 优化跨栏流转动画 (Travel Motion)

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue` (CSS 部分)

- [ ] **Step 1: 增强 TransitionGroup 动效**
- 增加 `translateX` 的距离。
- 添加 `scale(0.98)` 和 `blur(2px)` 的入场过渡。
