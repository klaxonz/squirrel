# 开源生产级视频播放器重构计划

> 项目代号: AspectPlayer  
> 创建日期: 2025-12-07  
> 状态: 进行中

## 一、现状分析

### 1.1 现有架构优点
- ✅ 清晰的 composables 分层架构
- ✅ Pinia store 集中状态管理
- ✅ 支持 HLS/DASH 流媒体协议
- ✅ 基础 TypeScript 类型定义 (`types/video-player.ts`)
- ✅ Context 注入减少 props drilling
- ✅ 键盘快捷键支持
- ✅ 双击快进/快退交互

### 1.2 待改进项
- ❌ Composables 仍为 JS，未完全 TypeScript 化
- ❌ 缺少插件系统和可扩展性
- ❌ 无主题/样式定制能力
- ❌ 无测试覆盖
- ❌ A11y（无障碍）支持不完善
- ❌ 无 i18n 国际化
- ❌ 与业务代码耦合（axios、API调用）
- ❌ 无法独立发布为 npm 包

### 1.3 现有文件结构
```
squirrel-frontend/src/
├── components/video-player/
│   ├── VideoPlayer.vue          # 主容器
│   ├── VideoPlayerCore.vue      # 核心视频元素
│   ├── VideoControls.vue        # 控制栏
│   ├── ProgressBar.vue          # 进度条
│   ├── PlaybackControls.vue     # 播放控制按钮
│   ├── VolumeControl.vue        # 音量控制
│   ├── QualitySelector.vue      # 清晰度选择
│   ├── SettingsMenu.vue         # 设置菜单
│   ├── TimeDisplay.vue          # 时间显示
│   ├── BufferingIndicator.vue   # 缓冲指示器
│   ├── SeekingIndicator.vue     # 快进快退指示器
│   ├── VolumeIndicator.vue      # 音量指示器
│   ├── KeyboardHelp.vue         # 快捷键帮助
│   ├── LoadingSpinner.vue       # 加载动画
│   └── ...
├── composables/
│   ├── useVideoPlayer.js        # 核心播放器逻辑
│   ├── useVideoControls.js      # 控制功能
│   ├── usePlayerContext.js      # Context 注入
│   ├── useMediaEvents.js        # 媒体事件处理
│   ├── useHlsPlayer.js          # HLS 支持
│   ├── useDashPlayer.js         # DASH 支持
│   ├── useKeyboardShortcuts.js  # 键盘快捷键
│   ├── useSubtitles.js          # 字幕处理
│   ├── useClickZones.js         # 点击区域
│   ├── useProgressBar.js        # 进度条交互
│   └── ...
├── stores/
│   └── playerStore.js           # Pinia 状态管理
└── types/
    └── video-player.ts          # 类型定义
```

---

## 二、目标架构

### 2.1 包结构
```
@aspect/player/
├── src/
│   ├── core/                    # 核心引擎（框架无关）
│   │   ├── Player.ts            # 播放器核心类
│   │   ├── EventEmitter.ts      # 事件系统
│   │   ├── MediaSource.ts       # 媒体源抽象
│   │   ├── StateManager.ts      # 状态管理
│   │   └── PluginManager.ts     # 插件管理器
│   │
│   ├── plugins/                 # 官方插件
│   │   ├── hls/                 # HLS 支持插件
│   │   │   ├── index.ts
│   │   │   └── HlsPlugin.ts
│   │   ├── dash/                # DASH 支持插件
│   │   │   ├── index.ts
│   │   │   └── DashPlugin.ts
│   │   ├── subtitles/           # 字幕插件
│   │   │   ├── index.ts
│   │   │   └── SubtitlesPlugin.ts
│   │   └── analytics/           # 播放分析插件
│   │       ├── index.ts
│   │       └── AnalyticsPlugin.ts
│   │
│   ├── vue/                     # Vue 绑定
│   │   ├── components/          # Vue 组件
│   │   │   ├── AspectPlayer.vue
│   │   │   ├── Controls.vue
│   │   │   ├── ProgressBar.vue
│   │   │   └── ...
│   │   ├── composables/         # Vue Composables
│   │   │   ├── usePlayer.ts
│   │   │   ├── usePlayerState.ts
│   │   │   └── usePlayerContext.ts
│   │   └── index.ts
│   │
│   ├── themes/                  # 主题系统
│   │   ├── base.css             # 基础样式
│   │   ├── dark.css             # 暗色主题
│   │   ├── light.css            # 亮色主题
│   │   └── variables.css        # CSS 变量定义
│   │
│   ├── i18n/                    # 国际化
│   │   ├── en.ts
│   │   ├── zh-CN.ts
│   │   └── index.ts
│   │
│   ├── types/                   # 类型定义
│   │   ├── player.ts
│   │   ├── plugin.ts
│   │   ├── events.ts
│   │   └── index.ts
│   │
│   └── index.ts                 # 主入口
│
├── dist/                        # 构建输出
├── docs/                        # 文档
├── examples/                    # 示例项目
├── tests/                       # 测试
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

### 2.2 核心类设计

```typescript
// core/Player.ts
class Player {
  private state: StateManager
  private events: EventEmitter
  private plugins: PluginManager
  private mediaElement: HTMLVideoElement | null
  
  constructor(options: PlayerOptions)
  
  // 生命周期
  mount(target: string | HTMLElement): void
  destroy(): void
  
  // 播放控制
  play(): Promise<void>
  pause(): void
  seek(time: number): void
  
  // 状态访问
  get currentTime(): number
  get duration(): number
  get volume(): number
  set volume(value: number)
  get paused(): boolean
  get ended(): boolean
  
  // 事件
  on<K extends keyof PlayerEvents>(event: K, handler: PlayerEvents[K]): void
  off<K extends keyof PlayerEvents>(event: K, handler: PlayerEvents[K]): void
  emit<K extends keyof PlayerEvents>(event: K, ...args: Parameters<PlayerEvents[K]>): void
  
  // 插件
  use(plugin: PlayerPlugin, options?: any): this
}
```

---

## 三、重构阶段

### Phase 1: 基础重构 [1-2周] ✅ 已完成
**目标**: TypeScript 化 + 解耦业务代码

- [x] 1.1 将核心 composables 迁移到 TypeScript
  - [x] `useVideoPlayer.js` → `useVideoPlayer.ts`
  - [x] `useVideoControls.js` → `useVideoControls.ts`
  - [x] `usePlayerContext.js` → `usePlayerContext.ts`
  - [x] `useMediaEvents.js` → `useMediaEvents.ts`
  - [x] `useHlsPlayer.js` → `useHlsPlayer.ts`
  - [x] `useDashPlayer.js` → `useDashPlayer.ts`
  - [x] `useKeyboardShortcuts.js` → `useKeyboardShortcuts.ts`
  - [x] `useClickZones.js` → `useClickZones.ts`
  - [x] `useProgressBar.js` → `useProgressBar.ts`
- [x] 1.2 将 `playerStore.js` 迁移到 `playerStore.ts`
- [x] 1.3 添加 TypeScript 配置 (`tsconfig.json`)
- [x] 1.4 添加类型检查脚本 (`npm run typecheck`)
- [x] 1.5 验证构建成功
- [x] 1.6 移除业务代码耦合 (`core/PlayerAdapter.ts`, `core/usePlayerAdapter.ts`)
  - [x] 抽象 axios 调用为回调 (IPlayerAdapter 接口)
  - [x] 抽象历史记录保存为回调 (saveProgress, getHistory)
  - [x] 抽象用户配置加载为回调 (loadConfig, saveConfig)
  - [x] 提供 LocalStorageAdapter (本地存储)
  - [x] 提供 ApiAdapter (HTTP API)
  - [x] 提供 CompositeAdapter (组合适配器)
- [x] 1.7 实现独立的 EventEmitter 类 (`core/EventEmitter.ts`) ✓ 已在 Phase 2 完成

### Phase 2: 插件系统 [1-2周] ✅ 已完成
**目标**: 可扩展的插件架构

- [x] 2.1 设计并实现 PluginManager (`core/PluginManager.ts`)
- [x] 2.2 定义插件接口和生命周期钩子 (`core/types.ts`)
  ```typescript
  interface PlayerPlugin {
    name: string
    version?: string
    install(context: PluginContext, options?: any): void
    destroy?(): void
  }
  
  interface PluginHooks {
    onInit?: () => void
    onPlay?: () => void
    onPause?: () => void
    onSeek?: (time: number) => void
    onTimeUpdate?: (currentTime: number, duration: number) => void
    onError?: (error: PlayerError) => void
    onDestroy?: () => void
  }
  ```
- [x] 2.3 将 HLS 重构为插件 (`plugins/hls/HlsPlugin.ts`)
- [x] 2.4 将 DASH 重构为插件 (`plugins/dash/DashPlugin.ts`)
- [x] 2.5 实现 EventEmitter 事件系统 (`core/EventEmitter.ts`)
- [x] 2.6 实现 usePluginSystem composable (`core/usePluginSystem.ts`)
- [x] 2.7 将字幕系统重构为插件 (`plugins/subtitles/SubtitlesPlugin.ts`)
  - [x] VTT/SRT 格式解析
  - [x] 样式自定义 (字体/颜色/背景/位置)
  - [x] 多轨道切换

### Phase 3: 主题与定制 [1周] ✅ 已完成
**目标**: 灵活的样式定制能力

- [x] 3.1 设计 CSS 变量系统 (`themes/variables.css`)
  - 颜色系统 (primary, bg, text, border, 状态色)
  - 控制栏、进度条、按钮、菜单样式变量
  - 动画、圆角、阴影、层级变量
  - 字体、间距系统
- [x] 3.2 实现主题切换机制 (`themes/useTheme.ts`)
  - 支持 dark/light/auto/custom 主题
  - 系统主题自动同步
  - localStorage 持久化
  - 动态 CSS 变量修改
- [x] 3.3 基础组件样式 (`themes/base.css`)
  - 播放器容器、控制栏、按钮
  - 进度条、音量控制、时间显示
  - 菜单、提示、字幕样式
  - 响应式断点支持
- [x] 3.4 暗色/亮色预设主题 (`themes/dark.css`, `themes/light.css`)
- [x] 3.5 预设主题配置 (YouTube/Bilibili/Netflix/Green/Purple)
- [x] 3.6 控制栏布局插槽系统 (`core/useControlsLayout.ts`)
  - [x] 预设布局 (default/minimal/youtube/bilibili)
  - [x] 控件注册/注销
  - [x] 区域分组 (left/center/right)
  - [x] 可见性控制
- [x] 3.7 图标系统可替换 (`core/useIcons.ts`)
  - [x] 内置 Material Design 图标 (25+ 图标)
  - [x] 自定义图标注册
  - [x] 图标集切换
  - [x] SVG 渲染

### Phase 4: 生产级特性 [2周] ✅ 已完成
**目标**: 达到生产环境标准

- [x] 4.1 完善 A11y 无障碍支持 (`core/useA11y.ts`)
  - [x] ARIA 属性完善 (playerAriaLabel, progressAriaLabel, volumeAriaLabel)
  - [x] 屏幕阅读器支持 (announce 公告函数)
  - [x] 焦点管理 (focusPlayer, trapFocus)
  - [x] 高对比度模式检测 (isHighContrast)
  - [x] 减少动画偏好 (prefersReducedMotion)
- [x] 4.2 i18n 国际化 (`i18n/`)
  - [x] 设计多语言架构 (types.ts, useI18n.ts)
  - [x] 实现语言包加载 (动态导入支持)
  - [x] 支持 zh-CN, en-US, ja-JP 三种语言
  - [x] 浏览器语言自动检测
  - [x] localStorage 持久化
- [x] 4.3 错误恢复机制 (`core/useErrorRecovery.ts`)
  - [x] 网络断线自动重试 (maxRetries, retryDelay)
  - [x] 清晰度自动降级 (quality-fallback)
  - [x] 播放失败恢复策略 (determineStrategy)
- [x] 4.4 性能监控 (`plugins/analytics/AnalyticsPlugin.ts`)
  - [x] 播放质量指标收集 (PlaybackMetrics)
  - [x] 缓冲事件分析 (bufferEvents)
  - [x] 错误率统计 (errorCount, errors)
  - [x] 带宽监控 (bandwidthSamples)
  - [x] 质量评分 (getQualityScore)
- [x] 4.5 移动端优化 (`core/useGestures.ts`)
  - [x] 手势支持 (滑动进度/音量、双击快进快退)
  - [x] 捏合缩放支持
  - [x] 触摸区域检测 (left/center/right)

### Phase 5: 测试与文档 [1-2周]
**目标**: 完善的测试覆盖和文档

- [ ] 5.1 单元测试
  - [ ] Core 模块测试
  - [ ] 插件测试
  - [ ] Composables 测试
  - [ ] Store 测试
- [ ] 5.2 组件测试
  - [ ] Vue 组件渲染测试
  - [ ] 交互测试
- [ ] 5.3 E2E 测试
  - [ ] 播放流程测试
  - [ ] 控制栏交互测试
  - [ ] 快捷键测试
- [ ] 5.4 API 文档
  - [ ] 核心 API 文档
  - [ ] 插件开发指南
  - [ ] 主题定制指南
- [ ] 5.5 示例项目
  - [ ] 基础使用示例
  - [ ] 插件开发示例
  - [ ] 自定义主题示例

---

## 四、关键设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 框架绑定 | Vue 3 优先，提供 Headless 核心 | 现有生态基础，未来可扩展 React/Svelte |
| 状态管理 | 内置轻量 StateManager，可选 Pinia | 独立性 + 与现有项目集成灵活性 |
| 样式方案 | CSS 变量 + 可选 Tailwind | 定制性强 + 包体积可控 |
| 流媒体支持 | 插件化 HLS.js / dash.js | 按需加载，减少核心包体积 |
| 打包工具 | Vite Library Mode | Tree-shaking + ESM/CJS/UMD 输出 |
| 类型系统 | 严格 TypeScript | 开发体验 + 运行时安全 |
| 测试框架 | Vitest + Vue Test Utils + Playwright | 现代化 + Vue 生态兼容 |
| 文档工具 | VitePress | 与 Vite 生态一致 |

---

## 五、API 设计

### 5.1 核心 API

```typescript
import { createPlayer, type PlayerOptions } from '@aspect/player'

const player = createPlayer({
  // 挂载目标
  target: '#player',
  
  // 视频源
  source: {
    src: 'https://example.com/video.mp4',
    type: 'video/mp4',
    poster: 'https://example.com/poster.jpg'
  },
  
  // 或 HLS/DASH 源
  source: {
    src: 'https://example.com/video.m3u8',
    type: 'application/x-mpegURL'
  },
  
  // 配置选项
  autoplay: false,
  muted: false,
  loop: false,
  volume: 100,
  playbackRate: 1,
  
  // 控制栏配置
  controls: {
    enabled: true,
    hideDelay: 3000,
    // 自定义布局
    layout: {
      left: ['play', 'prev', 'next', 'volume', 'time'],
      center: [],
      right: ['settings', 'pip', 'theater', 'fullscreen']
    }
  },
  
  // 快捷键
  keyboard: {
    enabled: true,
    global: false  // 是否全局监听
  },
  
  // 主题
  theme: 'dark',  // 'dark' | 'light' | 'auto'
  
  // 国际化
  locale: 'zh-CN',
  
  // 插件
  plugins: []
})

// 控制方法
player.play()
player.pause()
player.seek(60)
player.setVolume(80)
player.setPlaybackRate(1.5)
player.enterFullscreen()
player.exitFullscreen()
player.enterPiP()
player.exitPiP()

// 事件监听
player.on('play', () => {})
player.on('pause', () => {})
player.on('ended', () => {})
player.on('timeupdate', (time) => {})
player.on('volumechange', (volume) => {})
player.on('ratechange', (rate) => {})
player.on('fullscreenchange', (isFullscreen) => {})
player.on('error', (error) => {})

// 销毁
player.destroy()
```

### 5.2 Vue 组件 API

```vue
<template>
  <AspectPlayer
    ref="playerRef"
    :source="source"
    :autoplay="false"
    :muted="false"
    :loop="false"
    :volume="100"
    :poster="posterUrl"
    :plugins="plugins"
    theme="dark"
    locale="zh-CN"
    @play="onPlay"
    @pause="onPause"
    @ended="onEnded"
    @timeupdate="onTimeUpdate"
    @error="onError"
  >
    <!-- 自定义控制栏插槽 -->
    <template #controls-left>
      <CustomButton />
    </template>
    
    <!-- 自定义覆盖层 -->
    <template #overlay>
      <CustomOverlay />
    </template>
  </AspectPlayer>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { AspectPlayer, hlsPlugin, subtitlesPlugin } from '@aspect/player/vue'

const playerRef = ref()
const source = {
  src: 'https://example.com/video.m3u8',
  type: 'application/x-mpegURL'
}

const plugins = [
  hlsPlugin(),
  subtitlesPlugin()
]

// 通过 ref 访问播放器实例
const seekTo = (time: number) => {
  playerRef.value?.seek(time)
}
</script>
```

### 5.3 插件 API

```typescript
import { definePlugin, type Player, type PluginContext } from '@aspect/player'

export const myPlugin = definePlugin({
  name: 'my-plugin',
  version: '1.0.0',
  
  install(player: Player, options?: MyPluginOptions) {
    // 访问播放器状态
    const state = player.state
    
    // 监听事件
    player.on('play', () => {
      console.log('Video started playing')
    })
    
    // 扩展播放器方法
    player.extend('myMethod', () => {
      // 自定义逻辑
    })
    
    // 添加自定义 UI
    player.ui.addControl('my-button', {
      position: 'right',
      component: MyButtonComponent
    })
  },
  
  destroy() {
    // 清理逻辑
  }
})
```

---

## 六、里程碑

| 里程碑 | 目标日期 | 状态 |
|--------|----------|------|
| M1: TypeScript 迁移完成 | Week 2 | ✅ 已完成 |
| M2: 插件系统上线 | Week 4 | ⏳ 待开始 |
| M3: 主题系统完成 | Week 5 | ⏳ 待开始 |
| M4: 生产特性完成 | Week 7 | ⏳ 待开始 |
| M5: 测试覆盖 >80% | Week 8 | ⏳ 待开始 |
| M6: 文档完成 | Week 9 | ⏳ 待开始 |
| M7: v1.0.0 发布 | Week 10 | ⏳ 待开始 |

---

## 七、参考项目

- [Video.js](https://github.com/videojs/video.js) - 插件架构参考
- [Plyr](https://github.com/sampotts/plyr) - UI/UX 参考
- [VidStack](https://github.com/vidstack/player) - 现代化架构参考
- [Artplayer](https://github.com/zhw2590582/ArtPlayer) - 中文社区参考

---

## 八、变更日志

### 2025-12-07
- 创建重构计划文档
- 完成现状分析
- 定义目标架构
- 规划重构阶段
- **Phase 1 完成**: TypeScript 迁移
  - 迁移核心 composables: useVideoPlayer, useVideoControls, usePlayerContext, useMediaEvents, useHlsPlayer, useDashPlayer, useKeyboardShortcuts, useClickZones, useProgressBar
  - 迁移 playerStore 到 TypeScript
  - 添加 tsconfig.json 配置
  - 添加 vite-env.d.ts 类型声明
  - 安装 TypeScript 开发依赖
  - 验证类型检查和构建通过
