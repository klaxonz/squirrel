export interface VideoTab {
  label: string
  value: string
}

export const VIDEO_TABS: VideoTab[] = [
  { label: '全部', value: 'all' },
  { label: '未看', value: 'unread' },
]

export const VIDEO_LIBRARY_TABS: VideoTab[] = [
  { label: '喜欢', value: 'liked' },
  { label: '稍后看', value: 'later' },
]
