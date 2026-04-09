export const getSyncModeLabel = (mode: string | null | undefined) => {
  if (mode === 'full') return '全量'
  if (mode === 'incremental') return '增量'
  if (mode === 'extract') return '提取'
  return mode || '未知'
}
