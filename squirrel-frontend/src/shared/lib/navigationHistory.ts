/**
 * 应用层 history stack — 统一的"前进 / 后退"管理。
 *
 * 设计参照 macOS Finder / Safari / Apple Music 桌面 / Spotify 桌面的浏览器
 * 风格导航：
 *   - 维护一个有序 entry 栈，每个 entry 记录"我从哪来、当前页的滚动位置
 *     和过滤状态、父级标签是什么"；
 *   - 后退 / 前进只是把指针在栈里移动，并由 router 实际跳到目标 fullPath；
 *   - 任何 push/replace 都会记录目标 entry 的当前滚动位置，避免丢失上下文。
 *
 * 与浏览器自带的 `window.history` 的关系：
 *   - 浏览器 history 仍然承担"地址栏 / 前进后退按钮 / 刷新"的语义；
 *   - 本 store 负责"应用层上下文（滚动、过滤器、面包屑）"的恢复；
 *   - 同步策略：每次 `recordEntry` 后把当前 index 写入 `history.state._navIdx`
 *     以便 F5 / deep-link 进入时也能定位到正确的 entry（虽然此时只能恢复
 *     lastEntry 的 scrollY，过往 entry 的滚动状态已经在刷新时丢弃）。
 */

import type { RouteLocationNormalized } from 'vue-router'

export interface HistoryEntry {
  /** 唯一 id，调试 / key 用 */
  id: string
  /** 路由 fullPath，跳转目标 */
  fullPath: string
  /** 路由 name，路由比对用 */
  name?: string | symbol | null
  /** 当前页标题（来自 meta.title / 自动派生） */
  title: string
  /** 面包屑（不含当前页） */
  breadcrumbs: ReadonlyArray<{ label: string; to?: unknown }>
  /** 父级 section（用于面包屑第一级） */
  sectionLabel: string
  /** 进入该页时的滚动位置 */
  scrollY: number
  /** 进入该页时携带的过滤状态（路由 query 之外的自定义快照） */
  filters?: Record<string, unknown>
  /** 时间戳 */
  timestamp: number
}

const STORAGE_KEY = 'app:navigation-history:v1'
const MAX_ENTRIES = 50
const HISTORY_STATE_INDEX = '__navIndex'

let entries: HistoryEntry[] = []
let currentIndex = -1
let entrySeq = 0

function cloneEntries(): HistoryEntry[] {
  return entries.map((e) => ({ ...e, breadcrumbs: [...e.breadcrumbs] }))
}

function persist() {
  if (typeof sessionStorage === 'undefined') return
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({ entries: cloneEntries(), currentIndex, entrySeq }),
    )
  } catch {
    /* quota / unavailable — non-fatal */
  }
}

function restore(): boolean {
  if (typeof sessionStorage === 'undefined') return false
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return false
    const parsed = JSON.parse(raw) as {
      entries?: HistoryEntry[]
      currentIndex?: number
      entrySeq?: number
    }
    if (!Array.isArray(parsed.entries) || typeof parsed.currentIndex !== 'number') {
      return false
    }
    entries = parsed.entries
    currentIndex = parsed.currentIndex
    entrySeq = typeof parsed.entrySeq === 'number' ? parsed.entrySeq : entries.length
    return true
  } catch {
    return false
  }
}

function makeId(): string {
  entrySeq += 1
  return `nav-${Date.now().toString(36)}-${entrySeq}`
}

/**
 * 推入新 entry。语义对应浏览器的 pushState —— 进入新页。
 * 调用方需传入 entry 的元数据 + 当前滚动位置 + 过滤状态。
 */
export function pushEntry(input: Omit<HistoryEntry, 'id' | 'timestamp'>): HistoryEntry {
  const entry: HistoryEntry = {
    ...input,
    id: makeId(),
    timestamp: Date.now(),
  }

  // 任何"新 push"都会截断 forward 部分 —— 跟浏览器一致。
  if (currentIndex < entries.length - 1) {
    entries = entries.slice(0, currentIndex + 1)
  }
  entries.push(entry)
  if (entries.length > MAX_ENTRIES) {
    entries = entries.slice(entries.length - MAX_ENTRIES)
  }
  currentIndex = entries.length - 1
  syncHistoryState()
  persist()
  return entry
}

/**
 * 替换当前 entry。语义对应浏览器的 replaceState。
 * 用于"原地换内容"的场景（如 Tab 切换、SearchMode 切换、特殊筛选），
 * 避免历史栈被无意义的占位 entry 污染。
 */
export function replaceEntry(input: Omit<HistoryEntry, 'id' | 'timestamp'>): HistoryEntry {
  const entry: HistoryEntry = {
    ...input,
    id: makeId(),
    timestamp: Date.now(),
  }
  if (currentIndex < 0) {
    entries.push(entry)
  } else {
    entries[currentIndex] = entry
  }
  syncHistoryState()
  persist()
  return entry
}

/**
 * 更新当前 entry 的滚动位置 / 过滤状态（不改变指针）。
 */
export function patchCurrentEntry(patch: Partial<Pick<HistoryEntry, 'scrollY' | 'filters' | 'title'>>) {
  if (currentIndex < 0) return
  const current = entries[currentIndex]
  if (!current) return
  if (typeof patch.scrollY === 'number') current.scrollY = patch.scrollY
  if (patch.filters) current.filters = { ...current.filters, ...patch.filters }
  if (typeof patch.title === 'string' && patch.title) current.title = patch.title
  persist()
}

/**
 * 当前 entry。可空：冷启动尚未访问任何路由时返回 null。
 */
export function currentEntry(): HistoryEntry | null {
  return currentIndex >= 0 ? entries[currentIndex] ?? null : null
}

/**
 * 后退一步。返回新的 currentIndex + 新 entry；越界返回 null。
 * 调用方拿到 entry.fullPath 后应 router.replace 到目标（保持浏览器 history
 * 整洁），并让 router.afterEach 接管后续状态恢复。
 */
export function stepBack(): HistoryEntry | null {
  if (currentIndex <= 0) return null
  currentIndex -= 1
  const entry = entries[currentIndex]
  if (!entry) return null
  syncHistoryState()
  persist()
  return entry
}

export function canStepBack(): boolean {
  return currentIndex > 0
}

/**
 * 前进一步。语义对应浏览器 forward。
 */
export function stepForward(): HistoryEntry | null {
  if (currentIndex < 0) return null
  if (currentIndex >= entries.length - 1) return null
  currentIndex += 1
  const entry = entries[currentIndex]
  if (!entry) return null
  syncHistoryState()
  persist()
  return entry
}

export function canStepForward(): boolean {
  return currentIndex >= 0 && currentIndex < entries.length - 1
}

/**
 * 列出"还能去哪些地方"，用于 Back / Forward 按钮的长按下拉（Finder 风格）。
 * 返回的列表按"距离当前由近到远"排序。
 */
export function listBackCandidates(limit = 10): HistoryEntry[] {
  const out: HistoryEntry[] = []
  for (let i = currentIndex - 1; i >= 0 && out.length < limit; i -= 1) {
    const e = entries[i]
    if (e) out.push(e)
  }
  return out
}

export function listForwardCandidates(limit = 10): HistoryEntry[] {
  const out: HistoryEntry[] = []
  for (let i = currentIndex + 1; i < entries.length && out.length < limit; i += 1) {
    const e = entries[i]
    if (e) out.push(e)
  }
  return out
}

/**
 * 跳到栈内任意 entry（用于下拉菜单里直接点某条历史）。
 */
export function jumpToEntry(id: string): HistoryEntry | null {
  const idx = entries.findIndex((e) => e.id === id)
  if (idx < 0) return null
  currentIndex = idx
  const entry = entries[idx]
  if (!entry) return null
  syncHistoryState()
  persist()
  return entry
}

/**
 * 全部清空。登出 / 切换账号时调用。
 */
export function reset() {
  entries = []
  currentIndex = -1
  entrySeq = 0
  if (typeof sessionStorage !== 'undefined') {
    try {
      sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      /* ignore */
    }
  }
  syncHistoryState()
}

/**
 * 把 nav 指针同步到浏览器 history.state，便于 F5 / 深链场景定位 entry。
 */
function syncHistoryState() {
  if (typeof window === 'undefined' || !window.history?.state) return
  try {
    const next = { ...window.history.state, [HISTORY_STATE_INDEX]: currentIndex }
    window.history.replaceState(next, '')
  } catch {
    /* ignore */
  }
}

/**
 * 检查某个 fullPath 是不是"用户能直接前进/后退到的目标"。
 * 供 Router.afterEach 调用以决定是否刷新当前 entry 的 fullPath（防止 keep-alive
 * 切换 query 时的虚假 entry 增量）。
 */
export function isSameEntry(a: HistoryEntry, route: RouteLocationNormalized): boolean {
  if (a.name && route.name && a.name === route.name) return true
  return a.fullPath === route.fullPath
}

// 模块加载时尝试恢复一次（同一会话 F5 保留栈）。
restore()

// ── 响应式订阅（供 composable 包装） ──
type Listener = () => void
const listeners = new Set<Listener>()

function notify() {
  for (const l of listeners) l()
}

const wrappedPush = pushEntry
const wrappedReplace = replaceEntry
const wrappedPatch = patchCurrentEntry
const wrappedBack = stepBack
const wrappedForward = stepForward
const wrappedJump = jumpToEntry
const wrappedReset = reset

// 重新导出包装函数，让写入操作触发订阅。
export function pushEntryReactive(input: Parameters<typeof wrappedPush>[0]) {
  const r = wrappedPush(input)
  notify()
  return r
}
export function replaceEntryReactive(input: Parameters<typeof wrappedReplace>[0]) {
  const r = wrappedReplace(input)
  notify()
  return r
}
export function patchCurrentEntryReactive(patch: Parameters<typeof wrappedPatch>[0]) {
  wrappedPatch(patch)
  notify()
}
export function stepBackReactive() {
  const r = wrappedBack()
  notify()
  return r
}
export function stepForwardReactive() {
  const r = wrappedForward()
  notify()
  return r
}
export function jumpToEntryReactive(id: string) {
  const r = wrappedJump(id)
  notify()
  return r
}
export function resetReactive() {
  wrappedReset()
  notify()
}

export function subscribe(listener: Listener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}