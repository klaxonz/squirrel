import { VIDEO_TABS } from '../constants/videos'
import type { VideoTab } from '../constants/videos'

export function buildTabsWithCounts(counts: Record<string, number> | null | undefined, tabs: VideoTab[] = VIDEO_TABS) {
  const mapping = counts || {}
  return tabs.map((t) => ({ ...t, count: mapping[t.value] || 0 }))
}


