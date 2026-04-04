# 赛博工业风采集中心 (Cyber-Industrial Sync Center) 重构计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 彻底重构采集页 UI/UX，消除臃肿卡片感，采用 1px 细边框、直角设计、琥珀金/国际橙配色以及 LED 呼吸灯效果，打造精密工业仪表盘质感。

**Architecture:** 基于现有 Vue 3 组件进行样式重写，利用 Tailwind CSS 处理布局，自定义 CSS 实现发光 (Glow) 和点阵 (Dot-matrix) 效果。

**Tech Stack:** Vue 3, Tailwind CSS, Heroicons.

---

### Task 1: 定义全局主题变量与动画 (Theme & Animations)

**Files:**
- Modify: `squirrel-frontend/src/styles/index.css` (或创建新文件并在 main.ts 引入)

- [ ] **Step 1: 添加赛博工业风 CSS 变量与动画**

在全局样式文件中定义核心颜色和发光动画。

```css
:root {
  --cyber-orange: #FF4F00;
  --cyber-cyan: #00E5FF;
  --cyber-amber: #FFB300;
  --cyber-green: #00FF41;
  --cyber-border: rgba(255, 255, 255, 0.1);
}

@keyframes cyber-pulse-amber {
  0%, 100% { box-shadow: 0 0 4px var(--cyber-amber); opacity: 1; }
  50% { box-shadow: 0 0 12px var(--cyber-amber); opacity: 0.6; }
}

@keyframes cyber-pulse-cyan {
  0%, 100% { box-shadow: 0 0 4px var(--cyber-cyan); opacity: 1; }
  50% { box-shadow: 0 0 10px var(--cyber-cyan); opacity: 0.5; }
}

.glow-amber { animation: cyber-pulse-amber 2s infinite; }
.glow-cyan { animation: cyber-pulse-cyan 2s infinite; }

.font-dot {
  font-family: 'JetBrains Mono', 'Courier New', monospace; /* 备选点阵感字体 */
  letter-spacing: 0.05em;
}
```

- [ ] **Step 2: 验证样式加载**
确认页面背景色为 `#050505`。

- [ ] **Step 3: 提交**
```bash
git add squirrel-frontend/src/styles/index.css
git commit -m "style: add cyber-industrial theme variables and animations"
```

---

### Task 2: 重构 SyncControlBar (信号监控头)

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncControlBar.vue`

- [ ] **Step 1: 简化标题与摘要排版**

```vue
<template>
  <section class="flex flex-col gap-2 border-b border-white/10 pb-4 mb-4">
    <div class="flex items-baseline gap-4">
      <h1 class="text-2xl font-black tracking-[0.15em] text-white/90 uppercase font-mono">
        SIGNAL MONITORING
      </h1>
      <div class="h-1 w-1 rounded-full bg-orange-500 glow-amber"></div>
    </div>
    <p class="text-[10px] font-bold text-white/30 uppercase tracking-[0.3em] font-mono">
      {{ summary }}
    </p>
  </section>
</template>
```

- [ ] **Step 2: 提交**
```bash
git add squirrel-frontend/src/components/sync-center/SyncControlBar.vue
git commit -m "ui: redesign SyncControlBar with industrial header"
```

---

### Task 3: 重构 Lane 01 (SyncQueueBoard)

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncQueueBoard.vue`

- [ ] **Step 1: 去卡片化重绘行样式**
取消 `board-shell` 的渐变背景，改为透明背景加 1px 边框。

- [ ] **Step 2: 实现点阵排位与 LED 指示**
修改 `queue-row`：
- 背景改为 `transparent` 或 `bg-white/[0.02]`。
- 边框改为 `border-white/5`。
- 左侧 `#NO` 使用 `font-mono` 和冰青色。

- [ ] **Step 3: 提交**
```bash
git add squirrel-frontend/src/components/sync-center/SyncQueueBoard.vue
git commit -m "ui: redesign SyncQueueBoard with minimal line layout"
```

---

### Task 4: 重构 Lane 02 (SyncActiveRunBoard)

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncActiveRunBoard.vue`

- [ ] **Step 1: 实现离散能量条 (Power Bar)**
用一组 `div` 渲染进度，而不是原生 `<progress>`。

```vue
<div class="flex gap-1 h-1.5 w-full bg-white/5 mt-2">
  <div 
    v-for="i in 12" :key="i"
    class="flex-1 transition-colors duration-300"
    :class="i / 12 <= progress ? 'bg-orange-500' : 'bg-transparent'"
  ></div>
</div>
```

- [ ] **Step 2: 强化核心指标展示**
使用大号 `font-mono` 数字展示 `FOUND` 和 `SYNCED`。

- [ ] **Step 3: 提交**
```bash
git add squirrel-frontend/src/components/sync-center/SyncActiveRunBoard.vue
git commit -m "ui: redesign SyncActiveRunBoard with discrete power bars"
```

---

### Task 5: 重构 Lane 03 (SyncRecentRunBoard / TaskBoard)

**Files:**
- Modify: `squirrel-frontend/src/components/sync-center/SyncRecentRunBoard.vue`
- Modify: `squirrel-frontend/src/components/sync-center/SyncRecentTaskBoard.vue`

- [ ] **Step 1: 日志流化处理**
将每一行压缩为单行高度，使用更暗的配色，仅高亮成功/失败图标。

- [ ] **Step 2: 提交**
```bash
git add squirrel-frontend/src/components/sync-center/SyncRecentRunBoard.vue squirrel-frontend/src/components/sync-center/SyncRecentTaskBoard.vue
git commit -m "ui: redesign recent boards as minimal log streams"
```

---

### Task 6: 页面总装与背景优化 (SyncCenter.vue)

**Files:**
- Modify: `squirrel-frontend/src/views/SyncCenter.vue`

- [ ] **Step 1: 调整三栏间距与背景**
- 移除 `matrix-bg` 的过度装饰。
- 确保 `flow-shell` 的 grid 间距紧凑且对齐。
- 调整 `lane-strip` (顶部的 Queue/Active/Done 统计条) 的样式以匹配新主题。

- [ ] **Step 2: 最终视觉检查**
在浏览器中确认整体配色一致性，特别是“琥珀金”和“国际橙”的配合。

- [ ] **Step 3: 提交**
```bash
git add squirrel-frontend/src/views/SyncCenter.vue
git commit -m "ui: finalize SyncCenter layout and theme integration"
```
