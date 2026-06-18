# ponytail-audit · 前端全树扫描

> 工具：`ponytail-audit` skill（repo-wide，按删减量排序）
> 范围：`squirrel-frontend/src`
> 日期：2026-06-19
> 结果：14 条 finding，全部已记录并修复（见末尾「修复状态」表）。

---

## 14 条 finding（按删减量排序）

每行格式：`<tag> <删什么>. <替代方案>. [path]`
tag 含义：`delete:` 死代码 / `stdlib:` 标准库已提供 / `native:` 平台/依赖已提供 / `yagni:` 单实现抽象 / `shrink:` 同逻辑更短。

1. `delete:` **两套主题子系统并存**。`stores/theme.ts`（`useThemeStore`）被 `main.ts` + `AppLayout.vue` 用；`composables/useAppTheme.ts`（`useAppTheme`/`initializeAppTheme`）被 `Settings.vue` + `VideoPlay.vue` 用。两者各自维护**独立的模块级 `themeMode`/`systemTheme` ref**，且只有 `useAppTheme` 接了 `matchMedia('change')` 监听器——在 Settings 选的主题不会传到 store 的 `effectiveTheme`，OS 暗色切换对 store 路径不可见。替代：全部走 `useThemeStore`（已有 `effectiveTheme`/`isDark`），把 `matchMedia` 监听器挪进 `init()`。**注：这是真实的正确性/UX bug，不只是臃肿。** [src/stores/theme.ts, src/composables/useAppTheme.ts]

2. `shrink:` **`_prefetchNextTrack` 死分支**。`if (shuffle.value) { nextIdx = ... } else { nextIdx = ... }` 两个分支算的是同一个 `(queueIndex + 1) % queue.length`，注释还自承"Can't predict shuffle"。`shuffle` 判断和注释都是噪音。替代：`const nextIdx = (queueIndex.value + 1) % queue.value.length`。 [src/stores/musicPlayer.ts:364-388]

3. `stdlib:` **手搓 trace-id 生成器**。`generateTraceId` 用 32 次循环 + `Math.random()` 拼 32 字符 hex。替代：`crypto.randomUUID().replace(/-/g, '')`（一次调用，Electron renderer 有 `crypto`）。 [src/utils/axios.ts:6-13]

4. `native:` **手搓 `debounce` 重复造 `@vueuse/core` 的 `useDebounceFn`**（项目已依赖 `@vueuse/core`，6+ 文件在用）。本地版还做了个 `mousemove` 事件裁剪优化——唯一有价值的部分，但全仓只有 `ScheduledTasks.vue` 用 `debounce`（文本搜索，非 mousemove），该优化无消费者。替代：`useDebounceFn`，删 47 行 util。 [src/utils/debounce.ts]

5. `delete:` **`sortBreakpoints` 导出但零导入**。3 行 helper + JSDoc，零 caller。替代：nothing。 [src/composables/useSkeletonCount.ts:135-137]

6. `yagni:` **`CompositeAdapter` 是 1 产品的抽象**。写扇出到 N 个 adapter，读只取 `adapters[0]`；生产无 >1 adapter 构造点，`BackendPlayerAdapter extends LocalStorageAdapter` 直接继承而非组合。替代：删类；真要 multi-sink 再加。 [src/components/video-player/core/PlayerAdapter.ts:274-317]

7. `yagni:` **`MemoryAdapter` 是 engine 默认 fallback 但从不是真实 adapter**——生产接 `BackendPlayerAdapter`，存在仅为 `options.adapter ?? new MemoryAdapter()` 有非空默认。替代：让 `LocalStorageAdapter` 作 fallback（已是真实无操作基线），删 ~65 行。 [src/components/video-player/core/PlayerAdapter.ts:87-150, createPlayerEngine.ts:123]

8. `delete:` **`errorRecovery` 返回对象泄漏内部 helper**。`buildRecoveryContext`/`executeRetry`/`determineRecoveryStrategy`/`getNextLowerQuality`/`getStreamController`/`reloadCurrentSource` 暴露在返回对象上，但 engine 只用 `clearWaitingRecovery`/`scheduleWaitingRecovery`/`handleRecoveryError`/`reportFatalError`/`setRecoveryQualities`/`suppressWaitingRecovery`。替代：留作闭包局部变量，只返回用到的。 [src/components/video-player/core/error-recovery.ts:309-326]

9. `delete:` **`trackEvent` 缝线四处重复实现**——`IPlayerAdapter.trackEvent` + `MemoryAdapter.trackEvent` + `LocalStorageAdapter.trackEvent` + `BackendPlayerAdapter.trackEvent`，全是 `logger.debug('[X] Event', name, data)`，消费方是默认禁用的 `AnalyticsPlugin`（`enableAnalytics = false`）。替代：从 `IPlayerAdapter` 删 `trackEvent` 及四处实现；`AnalyticsPlugin` 若需要，直接订阅 engine events。 [src/components/video-player/core/PlayerAdapter.ts, BackendPlayerAdapter.ts:84-86]

10. `shrink:` ~~**`formatDate` 有不可达分支**~~ **【复核：误报，不修】**。初审认为尾块 `return formatDate(datePart)` 不可达。复核：该块在 `hasTimeComponent === true` 且 `>= 1 天` 的 fallthrough 路径上，`raw = "2026-06-19T10:30:00"` → `datePart = "2026-06-19"`（长度 10，不 `> 10`，不 `=== raw`）→ 走递归得到相对格式。是活的、有用的行为，**不修**。 [src/utils/dateFormat.ts:90-97]

11. `delete:` **`lib/utils.ts` 的 `valueUpdater` + `Updater` 类型**。注释明说"Avoids pulling in TanStack Table types since we don't depend on it"——即为不依赖一个没装的库而存在，且零 caller。替代：删两者。 [src/lib/utils.ts:10-18]

12. `delete:` **`monitorError` 是 3 行包装**（`Logger[level]('[ctx]', err)` 默认 warn），零 caller。替代：删文件，call site 若有需要直接 `Logger.warn`。 [src/utils/monitorError.ts]

13. `shrink:` ~~**`site-runtime-login-status.ts` token 大小写不一致**~~ **【复核：误报，不修】**。初审担心 `title.toLowerCase()` 后 CJK token 失配。复核：所有 ASCII token 已是小写（`'missing'`/`'error'`/`'expired'` 等），`.toLowerCase()` 对它们正确匹配；CJK token（`'未找到'`/`'风控'` 等）对 `.toLowerCase()` 是 no-op，在 lowercased `normalized` 里照样命中。逻辑正确，**不修**。 [src/utils/site-runtime-login-status.ts]

14. `delete:` **`useUserStore.error` ref 声明但从不写**——`fetchCurrentUser`/`login`/`register`/`updateProfile` 全 `return response` 不碰 `error.value`。死状态暴露给消费者。替代：删 ref。 [src/stores/user.ts:15]

---

`net: ~-220 行，-1 包装 util（debounce，走 @vueuse/core），-1 死导出（sortBreakpoints），-1 冗余子系统（useAppTheme），-1 未用 store 字段（error），可能 -1 IPlayerAdapter 方法（trackEvent，跨 4 个类）。`

---

## 修复状态

| # | finding | 状态 | 备注 |
|---|---------|------|------|
| 1 | 双主题子系统 | ✅ 已修 | 删 `useAppTheme.ts`，`Settings.vue`/`VideoPlay.vue` 改用 `useThemeStore`；`matchMedia` 监听挪进 store `init()` |
| 2 | `_prefetchNextTrack` 死分支 | ✅ 已修 | 单行取 nextIdx |
| 3 | `generateTraceId` 手搓 | ✅ 已修 | `crypto.randomUUID().replace(/-/g,'')` |
| 4 | 手搓 debounce | ✅ 已修 | `ScheduledTasks.vue` 改用 `useDebounceFn`，删 `utils/debounce.ts` |
| 5 | `sortBreakpoints` 死导出 | ✅ 已修 | 删 |
| 6 | `CompositeAdapter` YAGNI | ✅ 已修 | 删类 + 导出 |
| 7 | `MemoryAdapter` 默认 fallback | ✅ 已修 | engine fallback 改 `LocalStorageAdapter`，删 `MemoryAdapter` |
| 8 | `errorRecovery` 返回泄漏 | ✅ 已修 | 返回对象只留用到的 |
| 9 | `trackEvent` 缝线 | ✅ 已修 | 删接口方法 + 4 处实现 + engine/error-recovery 调用点 |
| 10 | `formatDate` 不可达分支 | ⚠️ 误报不修 | 复核为活的递归路径（带时间且 ≥1 天的日期），保留原行为 |
| 11 | `valueUpdater`/`Updater` 死类型 | ✅ 已修 | 删 |
| 12 | `monitorError` 死包装 | ✅ 已修 | 删文件（零 caller） |
| 13 | login-status token 大小写 | ⚠️ 误报不修 | ASCII token 已小写、CJK 对 toLowerCase no-op，逻辑正确 |
| 14 | `useUserStore.error` 死 ref | ✅ 已修 | 删 ref + 导出 |

验证：`npm run typecheck` + `npm run build:check` + `npm run lint` 全绿（0 error，3 warning 均为既有设计性 `any` 保留，非本次引入）。其中 #10/#13 复核为误报，未改代码（保留原行为）。实际净删约 **-260 行**：`useAppTheme.ts`（104 行）、`debounce.ts`（47 行）、`monitorError.ts`（5 行）、`PlayerAdapter.ts` 的 `MemoryAdapter`+`CompositeAdapter`+`trackEvent`（~160 行）、`errorRecovery` 返回对象泄漏项，以及散点死导出/死字段。
