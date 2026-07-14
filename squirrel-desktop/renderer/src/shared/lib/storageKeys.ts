/**
 * localStorage key 的单一真相源。
 *
 * 历史上这些 key 用品牌名做前缀（`squirrel_*` / `squirrel-app-*`），把技术层
 * 的持久化标识和面向用户的品牌名耦合在一起——改名或白标就要全站返工。
 * 现在统一改用**功能性命名**（`app:` 命名空间 + 用途描述）。
 *
 * 为了不让现有用户的本地数据"丢失"，每个 key 都声明了它的旧名（`legacy`）；
 * `getItem` / `removeItem` 会自动回退读取旧名并在读到时迁移到新名。调用方
 * 完全感知不到迁移，只需用这里的常量。
 */

export interface StorageKeyDef {
  /** 新的功能性 key（唯一真相）。 */
  current: string
  /** 需要迁移的旧 key（品牌前缀）。读到旧值时自动写入新 key 并清理旧 key。 */
  legacy?: string
}

export const STORAGE_KEYS = {
  theme: { current: 'app:theme', legacy: 'squirrel-app-theme' },
  serverUrl: { current: 'app:server-url', legacy: 'squirrel_server_url' },
  serverUrlVersion: { current: 'app:server-url:version', legacy: 'squirrel_server_url_version' },
  recentServerUrls: { current: 'app:server-url:recent', legacy: 'squirrel_recent_server_urls' },
  musicSearchHistory: { current: 'app:music:search-history', legacy: 'squirrel_music_search_history' },
  musicPlayerSession: { current: 'app:music:player-session', legacy: 'squirrel:music:player-session' },
  playerSubtitleStyle: { current: 'app:player:subtitle-style', legacy: 'squirrel-player-subtitle-style' },
  sitesConnectivity: { current: 'app:sites:connectivity', legacy: 'squirrel_connectivity_results' },
  sitesLoginStatus: { current: 'app:sites:login-status', legacy: 'squirrel_login_status_results' },
  sitesLastTested: { current: 'app:sites:last-tested', legacy: 'squirrel_last_tested_at' },
} as const satisfies Record<string, StorageKeyDef>

export type StorageKeyName = keyof typeof STORAGE_KEYS

/**
 * 读取一个 storage key，自动从 legacy key 迁移。
 *
 * - 优先读 `current`；读不到且有 `legacy` 时回退读 `legacy`。
 * - 命中 legacy 时把值搬到 `current` 并删除 `legacy`，保证只迁移一次。
 * - SSR 安全（`window` 不存在时返回 null）。
 */
export function getItem(name: StorageKeyName): string | null {
  if (typeof window === 'undefined') return null
  const def = STORAGE_KEYS[name]

  const value = window.localStorage.getItem(def.current)
  if (value !== null) return value

  if (!def.legacy) return null

  const legacyValue = window.localStorage.getItem(def.legacy)
  if (legacyValue === null) return null

  // 迁移：写入新 key，清理旧 key，只搬一次。
  window.localStorage.setItem(def.current, legacyValue)
  window.localStorage.removeItem(def.legacy)
  return legacyValue
}

/**
 * 写入一个 storage key（写到 `current`）。
 */
export function setItem(name: StorageKeyName, value: string): void {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(STORAGE_KEYS[name].current, value)
}

/**
 * 删除一个 storage key，同时清理可能残留的 legacy key。
 */
export function removeItem(name: StorageKeyName): void {
  if (typeof window === 'undefined') return
  const def = STORAGE_KEYS[name]
  window.localStorage.removeItem(def.current)
  if (def.legacy) window.localStorage.removeItem(def.legacy)
}
