/**
 * 播放进度的"乐观缓冲"。
 *
 * 组件卸载时对历史接口的 flush 上报是 fire-and-forget（onUnmounted 里
 * `void flushPendingReport()`），服务器可能还没落地。若用户"返回视频库 →
 * 立即重开同一视频"，详情请求可能先于上报返回，读到旧的 last_position。
 * 本模块记录最近一次本地观测位置，供详情加载（合并进 last_position）和
 * 列表刷新（按"已读"显示）在服务器响应到达前使用。
 *
 * 语义：只存"确实播放过（position > 0）"的位置；同一个视频保留最大值。
 * 条目在视频详情重新加载时被消费（consume），之后以服务器状态为准。
 */

const MAX_BUFFER_ENTRIES = 20
const pendingPositions = new Map<string, number>()

const normalizeId = (videoId: string | number | null | undefined): string =>
  String(videoId ?? '').trim()

/** 记录一次本地观测位置（仅 position > 0 且比既有值更新时覆盖）。 */
export function rememberPendingPosition(
  videoId: string | number | null | undefined,
  position: number,
): void {
  const key = normalizeId(videoId)
  if (!key || !Number.isFinite(position) || position <= 0) return

  const previous = pendingPositions.get(key)
  if (previous == null || position > previous) {
    pendingPositions.set(key, position)
  }
  if (pendingPositions.size > MAX_BUFFER_ENTRIES) {
    const oldestKey = pendingPositions.keys().next().value
    if (oldestKey !== undefined) pendingPositions.delete(oldestKey)
  }
}

/** 只读查看；不消费条目。 */
export function peekPendingPosition(videoId: string | number | null | undefined): number | null {
  const key = normalizeId(videoId)
  return pendingPositions.has(key) ? pendingPositions.get(key) ?? null : null
}

/** 消费并移除条目（视频详情加载时调用一次）。 */
export function consumePendingPosition(videoId: string | number | null | undefined): number | null {
  const key = normalizeId(videoId)
  const value = pendingPositions.get(key)
  if (value !== undefined) pendingPositions.delete(key)
  return value ?? null
}

/** Test-only escape hatch. */
export function __clearPendingPositionsForTests(): void {
  pendingPositions.clear()
}
