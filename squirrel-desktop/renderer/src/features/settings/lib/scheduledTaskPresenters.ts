import type { ScheduledTask, SchedulerStatistics } from '@/features/settings/types/scheduler'

/**
 * Pure presentation helpers for the scheduled-tasks view.
 *
 * Stateless formatters that map a scheduler status / interval unit / datetime
 * onto the badge text, Tailwind classes, and locale strings the template
 * renders. Extracted from ScheduledTasks.vue as a pure-utility module so the
 * view's script reads as query wiring → mutations, without interleaved lookup
 * tables. `getStatusCount` takes the statistics snapshot so the status
 * segmented-control can show live counts per filter.
 */

const UNIT_LABELS: Record<string, string> = {
  seconds: '秒',
  minutes: '分钟',
  hours: '小时',
  days: '天',
}

const UNIT_SECONDS: Record<string, number> = {
  seconds: 1,
  minutes: 60,
  hours: 60 * 60,
  days: 24 * 60 * 60,
}

const TASK_DISPLAY_NAMES: Record<string, string> = {
  MeiliReindexTask: '搜索索引重建',
  SubscriptionAutoImportTask: '订阅自动导入',
  CookieCloudSyncTask: 'CookieCloud 凭据同步',
  SubscriptionPendingReconcileTask: '待处理订阅校准',
  ThumbnailRefreshTask: '视频封面刷新',
  SubscriptionIncrementalUpdateTask: '订阅增量更新',
  SubscriptionFullUpdateTask: '订阅全量更新',
  CloudflareHeartbeatTask: 'Cloudflare 心跳检测',
}

const STATUS_LABELS: Record<string, string> = {
  enabled: '就绪',
  disabled: '暂停',
  running: '运行中',
  error: '异常',
}

/** Maps scheduler status → shared Badge variant (single chip vocabulary). */
const STATUS_BADGE_VARIANTS: Record<string, 'outline' | 'muted' | 'active' | 'error'> = {
  enabled: 'outline',
  disabled: 'muted',
  running: 'active',
  error: 'error',
}

/** Full label for an interval unit (seconds/minutes/hours/days). */
export const getUnitFull = (unit: string): string => UNIT_LABELS[unit] || unit

/**
 * Human-facing name for a task. Built-in scheduler class names are translated;
 * custom names are preserved, while unknown `*Task` identifiers are split into
 * readable words instead of leaking an implementation-style token into the UI.
 */
export const getTaskDisplayName = (
  task: Pick<ScheduledTask, 'name' | 'task_class'>,
): string => {
  const candidates = [task.name, task.task_class].filter(Boolean)
  for (const candidate of candidates) {
    if (TASK_DISPLAY_NAMES[candidate]) return TASK_DISPLAY_NAMES[candidate]
  }

  const name = task.name.trim()
  if (!/^[A-Z][A-Za-z0-9]+Task$/.test(name)) return name || '未命名任务'

  return name
    .replace(/Task$/, '')
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/([A-Z]+)([A-Z][a-z])/g, '$1 $2')
}

/** Normalizes an interval to the largest exact unit and returns natural copy. */
export const formatTaskInterval = (interval: number, unit: string): string => {
  const multiplier = UNIT_SECONDS[unit]
  if (!multiplier || !Number.isFinite(interval) || interval <= 0) {
    return `${interval} ${getUnitFull(unit)}`
  }

  const totalSeconds = interval * multiplier
  const units = [
    { unit: 'days', seconds: UNIT_SECONDS.days },
    { unit: 'hours', seconds: UNIT_SECONDS.hours },
    { unit: 'minutes', seconds: UNIT_SECONDS.minutes },
    { unit: 'seconds', seconds: UNIT_SECONDS.seconds },
  ]
  const normalized = units.find(candidate => totalSeconds % candidate.seconds === 0)
  if (!normalized) return `${interval} ${getUnitFull(unit)}`

  const value = totalSeconds / normalized.seconds
  if (value === 1) {
    const singularLabels: Record<string, string> = {
      seconds: '每秒',
      minutes: '每分钟',
      hours: '每小时',
      days: '每天',
    }
    return singularLabels[normalized.unit]
  }
  return `每 ${value} ${getUnitFull(normalized.unit)}`
}

/** Chinese label for a task status (enabled/disabled/running/error). */
export const getStatusText = (status: string): string => STATUS_LABELS[status] || status

/** Badge variant for a task status — use with shared `Badge`. */
export const getStatusBadgeVariant = (
  status: string,
): 'outline' | 'muted' | 'active' | 'error' =>
  STATUS_BADGE_VARIANTS[status] || 'muted'

/** Count of tasks in a given status filter ('all' returns the total). */
export const getStatusCount = (status: string, stats: SchedulerStatistics): number => {
  const counts: Record<string, number> = {
    all: stats.total_tasks,
    enabled: stats.active_tasks,
    disabled: Math.max(stats.total_tasks - stats.active_tasks, 0),
    running: stats.running_tasks,
    error: stats.error_tasks,
  }
  return counts[status] || 0
}

/** `MM-DD HH:mm` locale string, or null when empty/invalid. */
export const formatDateTime = (val: string | null | undefined): string | null => {
  if (!val) return null
  const date = new Date(val)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
