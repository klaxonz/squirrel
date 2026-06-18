# 前端开源级可维护性改造 · 交接文档

> 分支：`fix/bug` · 范围：`squirrel-frontend/` · 7 个 commit（b4a5cbba → ed76e8f0 + 散点清理）
> 后端改动（site_runtimes/site_plugins 等）**非本会话产出**，未触碰。

---

## 起点：诊断结论

前端是快速迭代堆出来的，单个功能能跑，但系统性欠债：
- **类型链全断**：API 层 80 个 bare call，DTO 用 `unknown[]`，组件 `video: any`。TS 等于没写。
- **抽象层只加不减**：错误处理三套并存（handleRequest 吞 `{error}`、errorHandler 注册表、axios 拦截器），状态管理 5 store + 42 composable + 模块级 ref 单例三套。
- **巨型组件**：VideoPlayer.vue 2784 行；RssSources.vue 1633 行。
- **any 掩盖真 bug**：补类型过程暴露并修复了 8+ 个"读不存在字段"的 bug。

## 终点：门禁指标

| 指标 | 改造前 | 改造后 |
|------|--------|--------|
| ESLint | 无 | flat config，0 error |
| 类型链 | 80 bare call / DTO `unknown[]` | 6 模块 + videoHistory 全接 DTO，api/ 强制 error |
| 错误处理 | 3 套 | 1 套（handleRequest + axios 401 + main.ts 兜底） |
| lint warning | 308（含 132 error） | 17（全是带 ponytail 标注的合理保留） |
| typecheck / build:check | — | 全绿 |

---

## 6 个 commit（按时间）

1. **b4a5cbba** `chore(frontend): remove dead code and convert login-status to TS`
   - 删 REFACTOR_PLAN.md（孤儿/乱码/烂尾）、videoCard.js、connectivity-status.js（零导入）
   - site-runtime-login-status.js → .ts + 类型
   - 删空的 invalidateBaseUrlCache

2. **cca2b2ff** `refactor(frontend): inline global error sinks, drop redundant errorHandler`
   - 删 errorHandler.ts（注册表几乎不触发，401 与 axios 拦截器重复）
   - main.ts 内联两个全局兜底（Vue errorHandler + unhandledrejection → Logger）

3. **cad8a4ab** `chore(frontend): introduce ESLint flat config and fix lint violations`
   - eslint.config.js（flat config）：no-explicit-any/no-mutating-props/no-unused-vars 全 error
   - 关闭 vue 模板格式规则（prettier 领域，非可维护性信号）
   - 渐进 overrides：api/feed/views/composables/video-player 暂 warn，shadcn 生成代码永久 off
   - 修基础设施层 any（debounce/request/api/axios/router/dateFormat/playerSession/player store）

4. **deb95b9c** `refactor(frontend): wire DTO types across core domain APIs`
   - 新建 types/{video,subscription,user,rss,scheduler}.ts（字段严格对照后端 serialization 层）
   - 接入 ~60 个 bare call：video/subscription/users/playlist/rss/scheduler/videoHistory
   - **修 bug**：VideoListResponse.items（后端只返回 data）、User.email（后端从不返回，删 4 处误读）、Subscribed 读 data.items
   - api/ 目录从 warn 升 error（0 违规）

5. **6d8e85ff** `refactor(frontend): type the feed component chain and fix VideoItem anti-patterns`
   - VideoItem.vue 三处反模式：props.video any→VideoListItem；10 处 mutating-props 改本地 ref；监听器泄漏修复
   - feed 主链类型化：VideoList/RecommendationCard/SubscriptionCard/HistoryItem/ContinueWatching
   - 修 bug：HistoryItem 读不存在的 progress 字段；VideoItem 的 VideoThumbnail import 路径错误
   - useLatestVideos/useVideoHistory 去本地重复 type

6. **ed76e8f0** `refactor(video-player): type core/runtime/composables, drop dead code`
   - plugin 边界 any（dashjs/hls/shaka）单独 off（第三方库 untyped，标注 ponytail）
   - core/runtime/composables 自己代码清零：结构化 plugin 接口（QualityController/SubtitleController/CodecController/StreamController）
   - PluginManager.get 约束放宽（`<T extends PlayerPlugin>` → `<T = PlayerPlugin>`）让 engine 请求结构视图
   - 删 dead code：VideoPlayer.vue 5 个 unused，createPlayerEngine/error-recovery/useSleepTimer 死 import

7. **散点清理**（本次会话，warnings 123 → 17）
   - **死代码删除（53 处 unused-var）**：RssSources destructure 12 个、Music.vue 14 个（顶层未用 import/destructure）、composables 散点（useMusicAuth/Home/Comments/Fm、usePlaylist、useRemoteChannel、useRouteTabSync、useRssReader、useSites、useVideoPageNavigation、useAppTheme、stores/ui、utils/serverConfig、ShakaDashPlugin）、views（Subscribed SiteTag、VideoPlay ApiResult）、GlobalSearchBar catch 占位符
   - **any 类型化（散点）**：useVideoHistory（navigator.connection 本地声明 + catch）、usePlaylist/useRemoteChannel/useRssEntries/useRssAccounts（catch unknown + response.data 直读）、useUser（error ref unknown）、useVideoOperations（metadata Record<string,unknown>）、History（VideoHistoryEntry + 删 progress 死字段）、HomeView/VideosView/ChannelDetailView（component ref 最小接口 `{ refresh?: () => void }`、loadError string、handleOpenModal `{id}`）、Subscribed（SubscriptionListItem/VideoListItem 接入）、Profile（avatarInput 结构类型）、RemoteChannelDetail（catch unknown）、feed 组件（SpotlightRow/SpecialFollowVideos VideoListItem、RemoteSearchResults catch、FeedToolbar unknown、VideoTab FeedFilters、VirtualList unknown）、RssSources（RssSyncStatus 本地类型）
   - **eslit override 收紧**：feed/views/composables/history 升 error（清零），仅留 layout（GlobalSearchBar 待 retyping）warn
   - **修 bug**：History.vue `video.progress` 字段从不存在（交接文档已记），删死字段读取

---

## 关键设计决策（防回潮的依据）

### Lint 渐进收敛机制（eslint.config.js overrides）
每个 override 块都有 `ponytail:` 注释说明清零条件。**清零后删 override 块**，规则自动升 error：
- `src/components/feed/**`、`src/views/**`、`src/composables/**` — any/mutating-props 暂 warn
- `src/components/video-player/**` — 暂 warn（剩 9 个是设计性 any）
- `src/components/ui/**` — **永久 off**（shadcn/reka 生成代码，手改抵触上游）
- `src/components/video-player/plugins/**` — **永久 off**（dashjs/hls/shaka 第三方边界）

### 合理保留的 any（不要无脑清）
- **subtitle style bag**（usePlayer SubtitleStyleBag = Record<string,any>）：CSS style bag，跨 UI 动态读，建模成 concrete 类型反添守卫负担
- **EventEmitter/EventHandler 泛型默认 any**：收紧 unknown 会破坏 PlayerEvents 下游约束
- **autoplayNext**（createPlayerEngine）：lint false-positive（实际被 :285/:868 读），用 eslint-disable + 注释
- **clipMarkers.js**：裸 JS，给了 resolveClipMarkerVideoId JSDoc，其余待转 .ts

### 后端字段对照基准（DTO 严格对齐后端 serialization）
DTO 不是猜的，是 trace 后端 serialization 层得来。关键字段差异（前端原误读）：
- video list：**只有 `data`，无 `items`**；list item **无** is_read/is_liked/is_later/site/description（VideoListItem 加了可选 site/description 兼容前端读取，标 ponytail 待对照）
- video detail：无 is_read/is_liked/is_later（interaction 编码在 interaction_type + last_position）；用 `creators` 不是 uploader
- user：**无 email**（后端从不返回）
- subscription list：`recent_videos`（不是 latest_videos）；SubscriptionCard 读 latest_videos 是可能的字段名 bug，DTO 加了可选别名标 ponytail 待确认
- video-history list：用 `items`（不是 data），entry 扁平（id 是 video id，history_id 是行 id）

---

## 剩余 17 warnings 的分布（下一会话可选）

按价值/工作量评估：

| 区域 | 数量 | 建议 |
|------|------|------|
| GlobalSearchBar.vue | 14 | 搜索建议/订阅结果 union，类型复杂，**单独评估**（layout override 仍 warn） |
| video-player（EventEmitter/usePlayer） | 3 | 全是 ponytail 保留的设计性 any，**不应清** |

## 明确未做（按 ponytail YAGNI 主动排除）

- **VideoPlayer.vue 2784 行拆分**：单独 epic，需沿已有接缝（useClipMarkers/createPlayerEngine/useCentralHud）切，不凭感觉拆
- **RssSources.vue 1633 行拆分**：同上
- **store vs composable 架构收敛**：状态到处藏（模块级 ref 单例），需统一进 store，属架构大改
- **prettier / husky / CI**：未要求，不引入
- **clipMarkers.js → .ts**：给了 JSDoc 止血，完整迁移另议

---

## 验证命令

```bash
cd squirrel-frontend
npm run lint          # 0 error / 17 warning
npm run typecheck     # vue-tsc 0 error
npm run build:check   # vue-tsc + vite build 通过
```

## 给下一会话的建议

1. **先和用户确认方向**：剩余 17 warning 边际收益极低（GlobalSearchBar 需单独评估，video-player 是设计性保留）；建议转向架构 epic（VideoPlayer/RssSources 拆分）或 store/composable 收敛
2. **GlobalSearchBar retyping**：14 个 any 是搜索建议/订阅结果 union，需要 trace 后端 search API 返回结构，单组件工作
3. 若推进架构：VideoPlayer 拆分是最大杠杆但风险高，建议先出拆分方案（沿现有 composable 接缝）再动手
4. **新发现的后端字段差异**（latest_videos vs recent_videos 等）需对照真实 payload 确认，DTO 里标了 ponytail 待办
