import { ref, type Ref } from 'vue'
import { Logger } from '@/shared/lib/logger'

/** A single log entry as returned by the logs API (only the copied fields). */
interface LogEntry {
  timestamp: string
  level: string
  logger: string
  line_num: number
  message: string
  trace_id?: string | null
}

/** Shape of the view's filter ref (only the copied fields). */
interface LogFilters {
  filename: string
  keyword: string
  level: string
}

export interface UseLogClipboardOptions {
  logs: Ref<LogEntry[]>
  filters: Ref<LogFilters>
}

/**
 * Owns the log-export clipboard: formats a single entry or the whole filtered
 * list as text, writes it to the clipboard, and surfaces a transient
 * "allCopied" flag the toolbar binds to for its success label. The two refs
 * (`logs`, `filters`) are injected read-only.
 */
export function useLogClipboard(options: UseLogClipboardOptions) {
  const { logs, filters } = options
  const allCopied = ref(false)
  let allCopiedTimer: ReturnType<typeof setTimeout> | null = null

  const flashAllCopied = () => {
    allCopied.value = true
    if (allCopiedTimer) clearTimeout(allCopiedTimer)
    allCopiedTimer = setTimeout(() => {
      allCopied.value = false
    }, 2000)
  }

  const copyLog = (logItem: LogEntry) => {
    let logText = ''
    logText += `时间: ${logItem.timestamp}\n`
    if (logItem.trace_id) {
      logText += `追踪编号: ${logItem.trace_id}\n`
    }
    logText += `级别: ${logItem.level}\n`
    logText += `日志器: ${logItem.logger}\n`
    logText += `行号: ${logItem.line_num}\n`
    logText += `\n内容:\n${logItem.message}\n`

    navigator.clipboard.writeText(logText).catch(err => {
      Logger.error('Failed to copy log', err)
      alert('复制失败，请手动复制')
    })
  }

  const copyAllLogs = () => {
    if (logs.value.length === 0) return

    let allLogsText = `日志导出 - 共 ${logs.value.length} 条\n`
    allLogsText += `文件: ${filters.value.filename}\n`
    if (filters.value.keyword) {
      allLogsText += `搜索: ${filters.value.keyword}\n`
    }
    if (filters.value.level) {
      allLogsText += `级别: ${filters.value.level}\n`
    }
    allLogsText += `导出时间: ${new Date().toLocaleString()}\n`
    allLogsText += `${'='.repeat(80)}\n\n`

    logs.value.forEach((logItem, index) => {
      allLogsText += `[${index + 1}] `
      allLogsText += `${logItem.timestamp} `
      if (logItem.trace_id) {
        allLogsText += `[${logItem.trace_id}] `
      }
      allLogsText += `${logItem.level} `
      allLogsText += `${logItem.logger}: `
      allLogsText += `${logItem.message}\n`
      allLogsText += `${'-'.repeat(80)}\n`
    })

    navigator.clipboard.writeText(allLogsText).then(flashAllCopied).catch(err => {
      Logger.error('Failed to copy logs', err)
      alert('复制失败，请手动复制')
    })
  }

  return { allCopied, copyLog, copyAllLogs }
}
