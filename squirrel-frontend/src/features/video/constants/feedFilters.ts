/** Shared option labels for the video feed filter popover and sort control. */

export type FilterOption = { value: string; label: string }

export const TIME_RANGE_OPTIONS: FilterOption[] = [
  { value: 'all', label: '不限' },
  { value: 'today', label: '今天' },
  { value: 'week', label: '本周' },
  { value: 'month', label: '本月' },
]

export const DURATION_OPTIONS: FilterOption[] = [
  { value: 'all', label: '不限' },
  { value: 'short', label: '短片' },
  { value: 'medium', label: '常规' },
  { value: 'long', label: '长片' },
]

export const CONTENT_TYPE_OPTIONS: FilterOption[] = [
  { value: 'all', label: '全部' },
  { value: 'CHANNEL', label: '频道' },
  { value: 'PLAYLIST', label: '列表' },
]

export const NSFW_OPTIONS: FilterOption[] = [
  { value: 'all', label: '全部' },
  { value: 'yes', label: '敏感' },
  { value: 'no', label: '安全' },
]

/** Sort is presentation order, not a filter — labels must read as sort criteria. */
export const SORT_OPTIONS: FilterOption[] = [
  { value: 'publish_date', label: '按上传日期' },
  { value: 'created_at', label: '按抓取日期' },
]
