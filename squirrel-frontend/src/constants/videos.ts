export interface VideoTab {
  label: string
  value: string
}

export const VIDEO_TABS: VideoTab[] = [
  { label: '全部', value: 'all' },
  { label: '未读', value: 'unread' },
  { label: '已读', value: 'read' },
  { label: '预告', value: 'preview' },
  { label: '喜欢', value: 'liked' },
  { label: '稍后看', value: 'later' },
]