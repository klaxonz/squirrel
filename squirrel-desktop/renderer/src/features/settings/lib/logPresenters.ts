/**
 * Pure presentation helpers for the log viewer.
 *
 * Extracted from LogViewer.vue so the log-timestamp / level-colour / file-size
 * formatters are reusable and audited in one place. Note `formatLogTimestamp`
 * is deliberately NOT named `formatTime`: the shared `@/shared/lib/dateFormat`
 * already exports a `formatTime` that formats a duration in seconds, whereas
 * this one extracts the `HH:mm:ss` clock portion from a backend log-line
 * timestamp string — a different operation that only collided on the name.
 */

/**
 * Extract the `HH:mm:ss` clock portion from a backend log-line timestamp
 * (`YYYY-MM-DD HH:mm:ss`). Falls back to the raw string when there's no space.
 */
export const formatLogTimestamp = (timestamp: string | null | undefined): string => {
  if (!timestamp) return ''
  const parts = timestamp.split(' ')
  return parts.length > 1 ? parts[1] : timestamp
}

const LEVEL_COLOR_CLASSES: Record<string, string> = {
  DEBUG: 'text-muted-foreground/40',
  INFO: 'text-info/80',
  WARNING: 'text-warning/80',
  ERROR: 'text-destructive',
  CRITICAL: 'text-destructive font-black',
}

const DEFAULT_LEVEL_COLOR_CLASS = 'text-muted-foreground'

/** Tailwind colour class for a log level (DEBUG/INFO/WARNING/ERROR/CRITICAL). */
export const getLevelColorClass = (level: string): string =>
  LEVEL_COLOR_CLASSES[level] || DEFAULT_LEVEL_COLOR_CLASS

/**
 * Human-readable byte size: `B` / `KB` / `MB` (2dp for KB/MB).
 * Reusable by any file-size surface (uploads, log files, attachments).
 */
export const formatFileSize = (bytes: number): string => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}
