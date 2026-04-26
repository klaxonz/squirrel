# Squirrel Frontend UI/UX Design Standards

> 本文档定义了 Squirrel 前端项目的 UI/UX 设计标准，旨在打造现代化、一致且易用的用户体验。

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Visual Design](#2-visual-design)
3. [Component Standards](#3-component-standards)
4. [Interaction Design](#4-interaction-design)
5. [Layout & Spacing](#5-layout--spacing)
6. [Responsive Design](#6-responsive-design)
7. [Accessibility](#7-accessibility)
8. [Animation & Motion](#8-animation--motion)
9. [Dark Theme Guidelines](#9-dark-theme-guidelines)
10. [Reference Sites](#10-reference-sites)

---

## 1. Design Principles

### 1.1 Core Principles

参考 **YouTube**, **Notion**, **Linear** 的设计哲学：

| Principle | Description | Implementation |
|-----------|-------------|----------------|
| **Clarity First** | 信息层次清晰，用户能快速找到目标 | 使用视觉权重区分重要/次要信息 |
| **Consistency** | 整个应用保持一致的设计语言 | 统一的组件、间距、色彩系统 |
| **Responsiveness** | 适配各种设备和屏幕尺寸 | 移动优先的响应式设计 |
| **Performance** | 感知速度快，无阻塞感 | 骨架屏、渐进式加载、流畅动画 |
| **Delight** | 微交互带来愉悦感 | 精心设计的过渡动画和反馈 |

### 1.2 Design Philosophy

```
功能性 > 美观性 > 装饰性
```

- **YouTube 风格**: 视频卡片使用略低饱和度的缩略图，hover 时轻微放大和提亮
- **Notion 风格**: 大量留白，信息密度适中，避免视觉噪音
- **Linear 风格**: 暗色系主调，精致的边框和阴影，subtle 的强调色

---

## 2. Visual Design

### 2.1 Color System

参考 **YouTube**, **Twitter/X**, **GitHub** 的配色策略：

#### Primary Colors

```css
/* 核心强调色 - 橙色调 */
--primary: 24 100% 50%;        /* #FF6600 - 主色调 */
--primary-hover: 20 100% 55%;  /* Hover 状态略亮 */
--primary-active: 18 100% 48%; /* Active 状态略暗 */

/* 语义色 */
--success: 142.1 70.6% 45.3%;  /* 绿色 - 成功状态 */
--warning: 37.9 97.2% 53.9%;   /* 黄色 - 警告状态 */
--error: 0 84.2% 60.2%;         /* 红色 - 错误状态 */
--info: 198 36% 41%;            /* 蓝色 - 信息状态 */
```

#### Neutral Palette (参考 GitHub)

```css
/* Light Theme */
--gray-50:  210 40% 98%;   /* #F8FAFC - 最浅背景 */
--gray-100: 210 40% 96%;   /* #F1F5F9 */
--gray-200: 214 32% 91%;   /* #E2E8F0 */
--gray-300: 214 28% 83%;   /* #CBD5E1 */
--gray-400: 215 16% 47%;   /* #64748B */
--gray-500: 215 20% 35%;   /* #475569 */
--gray-600: 215 25% 30%;   /* #334155 */
--gray-700: 215 28% 20%;   /* #1E293B */
--gray-800: 222 47% 11%;   /* #0F172A */
--gray-900: 222 47% 6%;    /* #0A0D14 */

/* Dark Theme */
--dark-50:  222 47% 8%;    /* #0D1117 - 深色背景 */
--dark-100: 222 47% 10%;   /* #161B22 */
--dark-200: 217 33% 17%;   /* #21262D */
--dark-300: 217 28% 25%;   /* #30363D */
```

#### Semantic Colors

```css
/* 文本色 */
--text-primary:   var(--foreground);
--text-secondary: var(--muted-foreground);
--text-tertiary: var(--muted-foreground);  /* 70% opacity */
--text-disabled: var(--muted-foreground);   /* 50% opacity */

/* 背景色 */
--bg-base:    var(--background);
--bg-raised:  var(--card);
--bg-overlay:  var(--overlay);

/* 边框色 */
--border-default: var(--border);
--border-subtle:   hsl(var(--border) / 0.5);
--border-strong:   hsl(var(--border) / 1.2);
```

#### Surface Elevation (参考 Linear)

```css
/* 使用 box-shadow 而非颜色区分层级 */
--surface-0: 0 0 0 1px var(--border);                              /* 平面 */
--surface-1: 0 1px 2px hsl(0 0% 0% / 0.04), 0 1px 3px hsl(0 0% 0% / 0.06);
--surface-2: 0 4px 6px -1px hsl(0 0% 0% / 0.06), 0 2px 4px -1px hsl(0 0% 0% / 0.04);
--surface-3: 0 10px 15px -3px hsl(0 0% 0% / 0.08), 0 4px 6px -2px hsl(0 0% 0% / 0.04);
```

### 2.2 Typography

参考 **Notion**, **Vercel**, **Stripe** 的字体策略：

#### Font Stack

```css
/* 主字体 - 清晰易读 */
--font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;

/* 等宽字体 - 代码/数据 */
--font-mono: 'JetBrains Mono', 'Fira Code', ui-monospace, monospace;

/* 中文字体 */
--font-cjk: 'Noto Sans SC', 'PingFang SC', 'Microsoft YaHei', sans-serif;
```

#### Type Scale (基于 16px)

```
Display:  48px / 1.1  / -0.02em  / 800  (页面大标题)
H1:       36px / 1.2  / -0.02em  / 700  (区块标题)
H2:       28px / 1.25 / -0.01em  / 600  (卡片标题)
H3:       22px / 1.3  / 0         / 600  (小标题)
H4:       18px / 1.4  / 0         / 600  (标签标题)
Body:     15px / 1.5  / 0         / 400  (正文)
Body-SM:  14px / 1.5  / 0         / 400  (次要正文)
Caption:  12px / 1.4  / 0.01em    / 500  (说明文字)
Label:    11px / 1.2  / 0.05em    / 600  (小标签, 全大写)
```

#### Font Weight Usage

- **900-800**: Logo, 大号数字
- **700-600**: 标题, 按钮文字
- **500**: 标签, 导航项
- **400**: 正文, 说明文字
- **300**: 次要说明

### 2.3 Spacing System

基于 **4px Grid** (参考 YouTube, Notion)：

```
4px   xs    - 紧凑间距，元素内部
8px   sm    - 相关元素间
12px  md    - 默认间距
16px  lg    - 分组元素间
24px  xl    - 区块间
32px  2xl   - 大区块间
48px  3xl   - 页面级间距
64px  4xl   - 大段落间
```

#### Spacing Token (Tailwind)

```js
// tailwind.config.js
spacing: {
  0: '0',
  0.5: '0.125rem',   // 2px
  1: '0.25rem',       // 4px
  1.5: '0.375rem',    // 6px
  2: '0.5rem',        // 8px
  2.5: '0.625rem',    // 10px
  3: '0.75rem',       // 12px
  3.5: '0.875rem',    // 14px
  4: '1rem',          // 16px
  5: '1.25rem',       // 20px
  6: '1.5rem',        // 24px
  7: '1.75rem',       // 28px
  8: '2rem',          // 32px
  9: '2.25rem',       // 36px
  10: '2.5rem',       // 40px
  12: '3rem',         // 48px
  14: '3.5rem',       // 56px
  16: '4rem',         // 64px
}
```

### 2.4 Border Radius

参考 **Apple**, **Linear**, **Vercel**：

```
4px    - 小按钮、标签、紧凑元素
8px    - 输入框、卡片 (默认)
12px   - 大卡片、模态框
16px   - 大容器
9996px - 药丸形按钮、全圆头像
```

```css
/* 统一 border-radius 变量 */
--radius-none: 0;
--radius-sm: 4px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
--radius-2xl: 20px;
--radius-full: 9996px;
```

---

## 3. Component Standards

### 3.1 Buttons

参考 **Stripe**, **Linear**, **GitHub** 的按钮设计：

#### Variants

```vue
<!-- Primary Button -->
<button class="btn btn-primary">
  Primary Action
</button>

<!-- Secondary Button -->
<button class="btn btn-secondary">
  Secondary Action
</button>

<!-- Ghost Button -->
<button class="btn btn-ghost">
  Ghost Action
</button>

<!-- Destructive Button -->
<button class="btn btn-destructive">
  Delete
</button>
```

#### Button Sizes

| Size | Height | Padding | Font | Border-radius |
|------|--------|---------|------|---------------|
| xs   | 28px   | 0 8px   | 12px | 4px          |
| sm   | 32px   | 0 12px  | 13px | 6px          |
| md   | 36px   | 0 16px  | 14px | 8px          |
| lg   | 42px   | 0 20px  | 15px | 8px          |
| xl   | 48px   | 0 24px  | 16px | 10px         |

#### Button States

```css
.btn {
  /* Default */
  background: var(--primary);
  color: var(--primary-foreground);
  border: 1px solid transparent;

  /* Hover */
  &:hover {
    filter: brightness(1.08);
    transform: translateY(-1px);
  }

  /* Active */
  &:active {
    transform: translateY(0);
    filter: brightness(0.95);
  }

  /* Disabled */
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    transform: none;
  }

  /* Focus */
  &:focus-visible {
    outline: 2px solid var(--ring);
    outline-offset: 2px;
  }
}
```

### 3.2 Cards

参考 **YouTube**, **Notion** 的卡片设计：

#### Video Card

```vue
<template>
  <article class="video-card">
    <div class="video-card__thumbnail">
      <img :src="thumbnail" :alt="title" loading="lazy" />
      <span class="video-card__duration">{{ duration }}</span>
      <div v-if="progress" class="video-card__progress">
        <div class="video-card__progress-fill" :style="{ width: `${progress}%` }" />
      </div>
    </div>
    <div class="video-card__info">
      <h3 class="video-card__title">{{ title }}</h3>
      <div class="video-card__meta">
        <span class="video-card__channel">{{ channel }}</span>
        <span class="video-card__dot">·</span>
        <span class="video-card__date">{{ date }}</span>
      </div>
    </div>
  </article>
</template>
```

#### Card Specifications

```
Video Card:
├── Thumbnail Container
│   ├── Aspect Ratio: 16:9
│   ├── Border-radius: 8px
│   ├── Hover: scale(1.02), brightness(1.05)
│   └── Transition: 200ms ease
├── Info Container
│   ├── Gap: 8px
│   └── Padding: 0
└── Title
    ├── Font: 14px / 500
    ├── Line-height: 1.4
    ├── Lines: 2 (clamp)
    └── Hover: color var(--primary)
```

### 3.3 Input Fields

参考 **Stripe**, **Linear** 的输入框设计：

#### Input Sizes

```css
.input {
  /* Height */
  --input-height-sm: 32px;   /* 小输入框 */
  --input-height-md: 40px;  /* 默认输入框 */
  --input-height-lg: 48px;  /* 大输入框 */

  /* Padding */
  --input-padding-x: 12px;

  /* Border */
  --input-border: 1px solid var(--border);
  --input-radius: 8px;

  /* Focus Ring */
  --input-ring: 0 0 0 3px var(--ring) / 0.15;
}
```

#### Input States

```css
.input-field {
  /* Default */
  background: var(--background);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);

  /* Hover */
  &:hover:not(:focus):not(:disabled) {
    border-color: var(--muted-foreground);
  }

  /* Focus */
  &:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: var(--input-ring);
  }

  /* Error */
  &.error {
    border-color: var(--error);
    &:focus {
      box-shadow: 0 0 0 3px hsl(var(--error) / 0.15);
    }
  }

  /* Disabled */
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: var(--muted);
  }
}
```

### 3.4 Dropdown / Select

参考 **GitHub**, **Notion** 的下拉菜单：

```vue
<template>
  <div class="select-wrapper">
    <select class="select-field">
      <option v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </option>
    </select>
    <ChevronDown class="select-icon" />
  </div>
</template>

<style scoped>
.select-wrapper {
  position: relative;
  display: inline-flex;
}

.select-field {
  appearance: none;
  padding-right: 2.5rem;
  cursor: pointer;
}

.select-icon {
  position: absolute;
  right: 12px;
  top: 50%;
  transform: translateY(-50%);
  pointer-events: none;
  color: var(--muted-foreground);
}
</style>
```

### 3.5 Tabs

参考 **YouTube**, **Notion** 的标签页设计：

```vue
<template>
  <nav class="tabs" role="tablist">
    <button
      v-for="tab in tabs"
      :key="tab.id"
      role="tab"
      :aria-selected="activeTab === tab.id"
      class="tab"
      :class="{ 'tab--active': activeTab === tab.id }"
      @click="$emit('update:activeTab', tab.id)"
    >
      {{ tab.label }}
    </button>
  </nav>
</template>

<style scoped>
.tab {
  /* 基线样式 */
  padding: 8px 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--muted-foreground);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: all 150ms ease;

  /* Hover */
  &:hover {
    color: var(--foreground);
    background: var(--accent);
  }

  /* Active */
  &.tab--active {
    color: var(--primary);
    border-bottom-color: var(--primary);
  }
}
</style>
```

### 3.6 Modal / Dialog

参考 **Linear**, **Notion**, **Figma** 的模态框：

```vue
<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="open" class="modal-overlay" @click.self="$emit('close')">
        <div class="modal" role="dialog" aria-modal="true">
          <header class="modal__header">
            <h2 class="modal__title">{{ title }}</h2>
            <button class="modal__close" @click="$emit('close')">
              <XIcon />
            </button>
          </header>
          <div class="modal__body">
            <slot />
          </div>
          <footer v-if="$slots.footer" class="modal__footer">
            <slot name="footer" />
          </footer>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--overlay);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
}

.modal {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--surface-3);
  max-width: 90vw;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}

.modal__title {
  font-size: 16px;
  font-weight: 600;
}

.modal__body {
  padding: 20px;
  overflow-y: auto;
  flex: 1;
}

.modal__footer {
  padding: 16px 20px;
  border-top: 1px solid var(--border);
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
```

---

## 4. Interaction Design

### 4.1 Hover States

参考 **YouTube**, **Stripe** 的 hover 设计：

| Element | Hover Effect | Duration |
|---------|--------------|----------|
| Button | `brightness(1.08)`, `translateY(-1px)` | 150ms |
| Card | `translateY(-2px)`, shadow increase | 200ms |
| Link | `color` change to primary | 150ms |
| Icon | `scale(1.1)` | 150ms |
| Thumbnail | `brightness(1.05)`, `scale(1.02)` | 200ms |
| Row item | `background` change | 100ms |

### 4.2 Click Feedback

```css
/* 按下时 */
.btn:active {
  transform: translateY(0) scale(0.98);
  transition-duration: 50ms;
}

/* 点击涟漪效果 (Material 风格可选) */
.click-ripple {
  position: relative;
  overflow: hidden;
}

.click-ripple::after {
  content: '';
  position: absolute;
  inset: 0;
  background: currentColor;
  opacity: 0;
  transition: opacity 150ms;
}

.click-ripple:active::after {
  opacity: 0.1;
}
```

### 4.3 Loading States

参考 **YouTube**, **Notion** 的加载状态：

#### Skeleton Loading

```vue
<template>
  <div class="skeleton-card">
    <div class="skeleton skeleton-thumbnail" />
    <div class="skeleton-content">
      <div class="skeleton skeleton-title" />
      <div class="skeleton skeleton-meta" />
    </div>
  </div>
</template>

<style scoped>
.skeleton {
  background: linear-gradient(
    90deg,
    var(--muted) 25%,
    var(--accent) 50%,
    var(--muted) 75%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s infinite;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
```

#### Spinner

```css
.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

### 4.4 Toast / Notification

参考 **Notion**, **Linear**, **Vercel**：

```vue
<template>
  <Teleport to="body">
    <TransitionGroup name="toast" tag="div" class="toast-container">
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="toast"
        :class="`toast--${toast.type}`"
      >
        <component :is="getIcon(toast.type)" class="toast__icon" />
        <span class="toast__message">{{ toast.message }}</span>
        <button class="toast__close" @click="removeToast(toast.id)">
          <XIcon />
        </button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.toast {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--surface-2);
  min-width: 300px;
  max-width: 400px;
}

.toast-enter-active,
.toast-leave-active {
  transition: all 300ms cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(100%) scale(0.9);
}
</style>
```

### 4.5 Context Menu

参考 **YouTube**, **macOS** 的右键菜单：

```vue
<template>
  <Teleport to="body">
    <Transition name="context-menu">
      <div
        v-if="visible"
        class="context-menu"
        :style="{ left: `${x}px`, top: `${y}px` }"
      >
        <button
          v-for="item in items"
          :key="item.id"
          class="context-menu__item"
          @click="handleClick(item)"
        >
          <component :is="item.icon" class="context-menu__icon" />
          <span>{{ item.label }}</span>
        </button>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 1000;
  min-width: 180px;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--surface-3);
  padding: 6px;
  animation: context-menu-enter 150ms ease;
}

@keyframes context-menu-enter {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.context-menu__item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: none;
  font-size: 14px;
  color: var(--foreground);
  border-radius: var(--radius-sm);
  cursor: pointer;
  text-align: left;

  &:hover {
    background: var(--accent);
  }

  &.destructive {
    color: var(--error);
    &:hover {
      background: hsl(var(--error) / 0.1);
    }
  }
}
</style>
```

---

## 5. Layout & Spacing

### 5.1 Page Structure

参考 **YouTube**, **Notion** 的页面布局：

```
┌─────────────────────────────────────────────────────────┐
│  Header / Topbar (56px)                                 │
│  ┌─────┬───────────────────────────────────────────────┤
│  │     │                                               │
│  │     │                                               │
│ Sidebar│           Main Content Area                    │
│ (240px)│                                               │
│  │     │                                               │
│  │     │                                               │
│  └─────┴───────────────────────────────────────────────┤
│  Mobile Bottom Nav (64px) - Mobile only                 │
└─────────────────────────────────────────────────────────┘
```

### 5.2 Grid System

```css
/* 最大内容宽度 */
--content-max-width: 1400px;

/* 栅格间距 */
--grid-gap-sm: 12px;
--grid-gap-md: 16px;
--grid-gap-lg: 24px;

/* 视频卡片网格 (参考 YouTube) */
.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 24px 16px;
}

/* 响应式调整 */
@media (max-width: 640px) {
  .video-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 16px 8px;
  }
}
```

### 5.3 Container Padding

```css
/* 页面容器 */
.page-container {
  padding: var(--page-gutter, 24px);
}

/* 卡片容器 */
.card-container {
  padding: var(--card-padding, 16px);
}

/* 移动端调整 */
@media (max-width: 768px) {
  .page-container {
    padding: 16px;
  }
}
```

---

## 6. Responsive Design

### 6.1 Breakpoints

```css
/* 移动优先断点 (参考 Bootstrap/Tailwind) */
--breakpoint-sm: 640px;   /* 手机横屏 */
--breakpoint-md: 768px;   /* 平板 */
--breakpoint-lg: 1024px;  /* 小笔记本 */
--breakpoint-xl: 1280px;  /* 桌面 */
--breakpoint-2xl: 1536px; /* 大屏桌面 */
```

### 6.2 Responsive Behaviors

| Component | Desktop (1024px+) | Tablet (768-1023px) | Mobile (<768px) |
|-----------|-------------------|---------------------|------------------|
| Sidebar | Fixed, 240px | Collapsible | Hidden, Bottom Nav |
| Video Grid | 4-5 columns | 3 columns | 2 columns |
| Page Padding | 24px | 20px | 16px |
| Header | Full height | Collapsed | Minimal |
| Modal | Centered | Centered, 90% width | Full screen |

### 6.3 Mobile-First Approach

```vue
<template>
  <!-- 移动端布局优先 -->
  <div class="layout">
    <!-- 移动端底部导航 -->
    <MobileNav class="md:hidden" />

    <!-- 桌面端侧边栏 -->
    <Sidebar class="hidden md:flex" />

    <!-- 内容区 -->
    <main class="content">
      <slot />
    </main>
  </div>
</template>
```

---

## 7. Accessibility

### 7.1 Color Contrast

参考 **WCAG 2.1** AA 标准：

```css
/* 最小对比度 */
--contrast-normal: 4.5;   /* 常规文本 */
--contrast-large: 3.0;    /* 大文本 (18px+) */

/* 示例 */
.text-primary {
  /* 白色文字在橙色背景上 */
  color: #fff;
  background: #FF6600;
  /* 对比度: 3.2:1 - 需要额外处理 */
}

.text-secondary {
  /* 深灰文字在白色背景上 */
  color: #475569;
  background: #fff;
  /* 对比度: 7.1:1 - 符合 AAA */
}
```

### 7.2 Focus States

```css
/* 焦点环样式 */
*:focus-visible {
  outline: 2px solid var(--ring);
  outline-offset: 2px;
}

/* 移除默认焦点样式 */
button:focus:not(:focus-visible) {
  outline: none;
}
```

### 7.3 ARIA Guidelines

```vue
<!-- 按钮 -->
<button role="button" aria-pressed="false" aria-label="Toggle theme">
  <MoonIcon />
</button>

<!-- 下拉菜单 -->
<div role="menu" aria-labelledby="menu-button">
  <button role="menuitem">Option 1</button>
</div>

<!-- 对话框 -->
<div role="dialog" aria-modal="true" aria-labelledby="dialog-title">
  <h2 id="dialog-title">Confirm Action</h2>
</div>

<!-- 选项卡 -->
<div role="tablist">
  <button role="tab" aria-selected="true" aria-controls="panel-1">Tab 1</button>
</div>
```

### 7.4 Keyboard Navigation

```css
/* 焦点顺序 */
.tab-order {
  tab-index: 0;
}

/* 跳转到内容 */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: var(--primary);
  color: white;
  padding: 8px;
  z-index: 100;
}

.skip-link:focus {
  top: 0;
}
```

---

## 8. Animation & Motion

### 8.1 Animation Principles

参考 **Apple**, **Google Material** 的动效哲学：

1. **Purposeful** - 每个动画都有意义，帮助用户理解界面
2. **Quick** - 快速响应，不让用户等待
3. **Natural** - 符合物理世界的运动规律
4. **Consistent** - 整个应用保持一致的运动语言

### 8.2 Timing Functions

```css
/* 标准缓动曲线 */
--ease-default: cubic-bezier(0.4, 0, 0.2, 1);      /* 通用 */
--ease-in: cubic-bezier(0.4, 0, 1, 1);              /* 进入 */
--ease-out: cubic-bezier(0, 0, 0.2, 1);             /* 退出 */
--ease-bounce: cubic-bezier(0.34, 1.56, 0.64, 1);   /* 弹性 */

/* 动画时长 */
--duration-instant: 50ms;   /* 即时反馈 */
--duration-fast: 150ms;     /* 快速过渡 */
--duration-normal: 200ms;   /* 标准过渡 */
--duration-slow: 300ms;     /* 较慢过渡 */
--duration-slower: 500ms;   /* 页面切换 */
```

### 8.3 Common Animations

```css
/* 淡入淡出 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity var(--duration-normal) var(--ease-default);
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 滑入 */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all var(--duration-normal) var(--ease-out);
}
.slide-up-enter-from {
  opacity: 0;
  transform: translateY(16px);
}
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

/* 缩放 */
.scale-enter-active,
.scale-leave-active {
  transition: all var(--duration-normal) var(--ease-bounce);
}
.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}

/* 列表过渡 */
.list-move {
  transition: all var(--duration-slow) var(--ease-out);
}
.list-enter-active,
.list-leave-active {
  transition: all var(--duration-normal) var(--ease-default);
}
```

### 8.4 Page Transitions

```css
/* 页面切换 - 淡入 + 轻微上移 */
.page-enter-active {
  animation: page-in 300ms var(--ease-out);
}
.page-leave-active {
  animation: page-out 200ms var(--ease-in);
}

@keyframes page-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes page-out {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}
```

---

## 9. Dark Theme Guidelines

### 9.1 Color Adjustments

```css
/* 深色主题特殊处理 */
[data-theme="dark"] {
  /* 提高文字对比度 */
  --foreground: 210 40% 98%;

  /* 降低背景饱和度 */
  --background: 222 47% 6%;
  --card: 222 47% 9%;

  /* 边框更柔和 */
  --border: 217 33% 17%;

  /* 减少纯白使用 */
  --muted-foreground: 215 20% 65%;

  /* 图片处理 */
  img {
    opacity: 0.9;
  }
}
```

### 9.2 Elevation in Dark Mode

```css
[data-theme="dark"] {
  /* 深色模式下用更亮的边框代替阴影 */
  --surface-1: 0 0 0 1px var(--border);
  --surface-2: 0 0 0 1px var(--border), 0 4px 8px hsl(0 0% 0% / 0.3);
  --surface-3: 0 0 0 1px var(--border), 0 8px 16px hsl(0 0% 0% / 0.4);
}
```

### 9.3 Interactive States

```css
[data-theme="dark"] {
  /* 深色模式 hover 更微妙 */
  .card:hover {
    background: hsl(var(--card) + 2%); /* 略微变亮 */
    border-color: var(--muted-foreground);
  }

  /* 按钮 */
  .btn:hover {
    filter: brightness(1.1);
  }

  /* 输入框 */
  .input:focus {
    border-color: var(--primary);
    box-shadow: 0 0 0 3px hsl(var(--primary) / 0.2);
  }
}
```

---

## 10. Reference Sites

以下网站的设计实践值得参考：

### 10.1 Video & Media

| Site | Reference Points |
|------|------------------|
| **YouTube** | 视频卡片布局、缩略图展示、进度条、播放控制 |
| **Twitch** | 暗色主题、实时状态、聊天集成 |
| **Vimeo** | 简洁设计、高质量缩略图、播放器设计 |

### 10.2 Productivity & SaaS

| Site | Reference Points |
|------|------------------|
| **Notion** | 空白布局、卡片设计、侧边导航 |
| **Linear** | 暗色主题、精致边框、流畅动画 |
| **Vercel** | 极简设计、清晰层次、文档布局 |
| **Stripe** | 表格设计、表单验证、按钮状态 |

### 10.3 Social & Communication

| Site | Reference Points |
|------|------------------|
| **Twitter/X** | 信息流设计、卡片组件、快捷操作 |
| **Reddit** | 列表布局、投票设计、评论系统 |
| **Discord** | 服务器列表、频道导航、暗色主题 |

### 10.4 Design Systems

| Site | Reference Points |
|------|------------------|
| **Apple Human Interface** | 交互原则、视觉设计、图标系统 |
| **Google Material Design** | 动效设计、组件规范、色彩系统 |
| **Figma** | 界面布局、属性面板、工具栏设计 |

---

## Appendix: Quick Reference

### Color Variables

```css
/* 主要色 */
--primary:           hsl(24 100% 50%);
--primary-hover:     hsl(20 100% 55%);
--primary-active:    hsl(18 100% 48%);
--primary-foreground: hsl(0 0% 100%);

/* 背景色 */
--background:        hsl(210 40% 98%);
--foreground:        hsl(222 47% 11%);
--card:              hsl(0 0% 100%);
--muted:             hsl(210 40% 96%);

/* 边框色 */
--border:            hsl(214 32% 91%);
--input:             hsl(214 32% 91%);
--ring:              hsl(24 100% 50%);

/* 语义色 */
--success:           hsl(142 70% 45%);
--warning:           hsl(37 97% 54%);
--error:             hsl(0 84% 60%);
```

### Spacing Scale

```
2px  - 4px   - xs
4px  - 8px   - sm
6px  - 12px  - md
8px  - 16px  - lg
12px - 24px  - xl
16px - 32px  - 2xl
24px - 48px  - 3xl
```

### Border Radius

```
4px   - 紧凑元素 (tags, badges)
8px   - 默认 (buttons, inputs, cards)
12px  - 大卡片 (modals, panels)
16px  - 大容器
9996px - 药丸形 (pills, avatars)
```

### Typography Scale

```
36px - 48px  - Display
24px - 32px  - H1
20px - 24px  - H2
16px - 20px  - H3
14px - 16px  - Body
12px - 14px  - Caption
11px - 12px  - Label
```

---

> Last Updated: 2026-04-26
> Version: 1.0.0
