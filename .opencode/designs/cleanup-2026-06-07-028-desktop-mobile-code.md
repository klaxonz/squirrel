# 桌面端清理移动端代码 — 设计方案

## 根因

`squirrel-frontend` 是 Electron 桌面端的渲染进程，不支持移动端，但遗留了大量移动端专用代码路径，包括：移动端检测 composable、底部导航栏、触摸手势引擎、safe-area/100dvh/dvh CSS、RSS 阅读器移动端 UI 分支。

## 修复思路

1. **删除 5 个移动端专用文件** — `useMobile.ts`、`MobileNavigation.vue`、`MobileNav.vue`、`useGestures.ts`、`mobileControls.js`
2. **修改 AppLayout.vue** — 移除 `isMobile` 条件分支和 MobileNavigation 引用，删除 h-nav spacer
3. **修改 sidebar.ts** — 从 `NavigationItem` 接口删除 `mobileLabel`/`showOnMobile`，删除 `MOBILE_NAV_ITEMS` 导出，清除 12 个导航项的对应字段
4. **修改 VideoPlayer.vue** — 移除 `mobileControls.js` 导入和 `lastPointerType`，内联 `shouldAutoHideControls`，移除 touch 相关指针类型守卫（桌面端永远是 mouse）
5. **修改 usePlayer.ts** — 移除 `useGestures` 导入/使用，移除 `enableGestures`/`onTouchTap` 选项
6. **修改 useRssReader.ts/RssSources.vue** — 移除 `isMobile`/`showMobileReaderSettings`/`mobileReaderSettingsRef`/`checkIfMobile` 及相关 template
7. **清理移动端 CSS** — `index.html` viewport meta 简化、`App.vue` 100dvh → 100vh、`VirtualList.vue` 移除 `-webkit-overflow-scrolling: touch`、`MusicImmersivePlayer.vue` 100dvh → 100vh、移除 `--mobile-nav-height`、移除 `GlobalMusicPlayerBar.vue` 中依赖移动导航的断点样式

## 涉及文件

- 删除: `useMobile.ts`, `MobileNavigation.vue`, `MobileNav.vue`, `useGestures.ts`, `mobileControls.js`
- 修改: `AppLayout.vue`, `sidebar.ts`, `VideoPlayer.vue`, `usePlayer.ts`, `index.html`, `App.vue`, `VirtualList.vue`, `MusicImmersivePlayer.vue`, `layout.css`, `GlobalMusicPlayerBar.vue`, `useRssReader.ts`, `RssSources.vue`

## 不涉及

- `@media (max-width: 768px/767px/640px/639px)` 断点保留（属于桌面窗口缩放的响应式布局，非移动专用）
- `squirrel-desktop/` 中的 Android UA（功能性内容请求头）
- 不碰后端/SDK/插件代码

## 潜在风险

- 视频播放器指针/点击逻辑改动：`shouldHandlePointerVisibility` 和 `shouldTogglePlayOnVideoClick` 在桌面上恒为 true，移除守卫后行为不变
- RSS 阅读器移除 Sheet 抽屉后，桌面端阅读始终使用侧栏面板
- `100dvh` → `100vh`：Electron 固定视口下等价，无行为变化
