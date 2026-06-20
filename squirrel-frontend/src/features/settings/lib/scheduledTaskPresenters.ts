import type { SchedulerStatistics } from '@/features/settings/types/scheduler'

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

const STATUS_LABELS: Record<string, string> = {
  enabled: '就绪',
  disabled: '暂停',
  running: '运行中',
  error: '异常',
}

const STATUS_BADGE_CLASSES: Record<string, string> = {
  enabled: 'border-border/50 bg-background text-foreground',
  disabled: 'border-border/50 bg-muted text-muted-foreground',
  running: 'border-primary/20 bg-primary/10 text-primary',
  error: 'border-destructive/20 bg-destructive/10 text-destructive',
}

const DEFAULT_BADGE_CLASS = 'border-border/50 bg-muted text-muted-foreground'

/** Full label for an interval unit (seconds/minutes/hours/days). */
export const getUnitFull = (unit: string): string => UNIT_LABELS[unit] || unit

/** Chinese label for a task status (enabled/disabled/running/error). */
export const getStatusText = (status: string): string => STATUS_LABELS[status] || status

/** Tailwind badge classes for a task status. */
export const getStatusBadgeClass = (status: string): string =>
  STATUS_BADGE_CLASSES[status] || DEFAULT_BADGE_CLASS

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
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
