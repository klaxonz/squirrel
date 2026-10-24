export type HomeInboxFilter = 'all' | 'unread' | 'special'

export const HOME_INBOX_FILTER_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'unread', label: '未看' },
  { value: 'special', label: '特别关注' },
] as const
