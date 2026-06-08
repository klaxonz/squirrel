# YouTubei SESSION_CACHE 无界增长修复方案

## 根因

`SESSION_CACHE`（`youtubei_core.mjs:17`）是 `new Map()`，以 auth 模式为 key 缓存 `Innertube` 运行时实例。`getRuntime()` 每次按 key 写入新条目，但**没有任何 eviction 机制**。Cookie 变更、OAuth 刷新或长期运行后，Map 无界增长。

## 修复思路

将 `Map` 替换为 **LRU Cache（最大 3 条目）**，利用 `Map` 的插入顺序特性：

- `get(key)` → 删除再重新插入，将条目移到末尾（"最近使用"）
- `set(key, value)` → 已存在先删除；插入后若超 max，删除第一个 key（最久未使用）
- 对外暴露同一接口（`get/set/delete/clear`），仅需改动第 17 行和 `getRuntime` 中两处调用

3 条上限已足够覆盖典型场景：匿名 + cookie + OAuth，且比建议方向的 "最大 3 条目" 更保守可控。

## 涉及文件

- `squirrel-desktop/src/playback/providers/youtube/youtubei_core.mjs` — LRUMap 类 + SESSION_CACHE 声明

## 潜在风险

- LRU 语义改变：之前 Map 保留所有条目，现在超过 3 后自动驱逐。对同一 key 连续调用 `get` 不受影响；不同 auth 模式频繁切换可能导致重复创建。但 `Innertube.create()` 本身已有开销预期，且 3 条在典型场景中足够。
- 无 TTL：只用 LRU 驱逐，OAuth token 过期后的 session 仍可能被命中。但结合 OAuth 的 `signIn` 校验（已在 `getRuntime` 中），过期时会 fallback。3 条上限保证旧 session 很快被新访问驱逐。
