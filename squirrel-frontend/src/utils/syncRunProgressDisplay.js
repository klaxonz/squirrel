const RECENT_STATUS_LABELS = {
  success: '成功',
  failed: '失败',
  running: '已转提取',
  queued: '排队中',
  deferred: '已延后',
  timeout: '超时',
}

export function formatActiveRunProgress(item = {}) {
  return {
    label: item.progress_label || '进行中',
    showPercent: false,
    showRail: false,
  }
}

export function formatRecentRunProgress(run = {}) {
  return {
    summaryText: RECENT_STATUS_LABELS[run.status] || run.progress_label || run.status || '未知',
    showPercent: false,
  }
}
