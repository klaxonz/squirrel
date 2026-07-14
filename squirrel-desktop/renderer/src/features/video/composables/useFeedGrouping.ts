import { computed, type ComputedRef, type Ref } from 'vue'
import type { VideoListItem } from '@/features/video/types/video'

/**
 * Date-bucket grouping for a feed video list.
 *
 * Buckets videos into 今天 / 昨天 / 本周 / 本月 / `YYYY年M月` sections based on
 * `uploaded_at` (falling back to `created_at`), in fixed display order. Items
 * without a date are dropped.
 *
 * Extracted from Subscribed.vue as a pure presentation transform — the bucketing
 * rule (today/yesterday/this-week/this-month/year-month, with the 7-/30-day
 * thresholds) is reusable by any feed-style surface and easier to reason about
 * in isolation than interleaved with pagination + observer wiring.
 */
export interface FeedGroup {
  title: string
  videos: VideoListItem[]
}

export interface UseFeedGroupingOptions {
  feedItems: ComputedRef<VideoListItem[]> | Ref<VideoListItem[]>
}

export interface UseFeedGroupingReturn {
  videoGroups: ComputedRef<FeedGroup[]>
}

// Display order of the non-year buckets; year-month buckets sort after.
const BUCKET_ORDER = ['今天', '昨天', '本周', '本月']

export function useFeedGrouping(options: UseFeedGroupingOptions): UseFeedGroupingReturn {
  const { feedItems } = options

  const videoGroups = computed<FeedGroup[]>(() => {
    const groups: Record<string, VideoListItem[]> = {}
    feedItems.value.forEach((video) => {
      const publishDate = video.uploaded_at || video.created_at
      if (!publishDate) return

      const date = new Date(publishDate)
      const now = new Date()
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
      const yesterday = new Date(today)
      yesterday.setDate(yesterday.getDate() - 1)

      let title = ''
      const videoDate = new Date(date.getFullYear(), date.getMonth(), date.getDate())
      if (videoDate.getTime() === today.getTime()) title = '今天'
      else if (videoDate.getTime() === yesterday.getTime()) title = '昨天'
      else {
        const diffDays = Math.floor((today.getTime() - videoDate.getTime()) / (1000 * 60 * 60 * 24))
        if (diffDays < 7) title = '本周'
        else if (diffDays < 30) title = '本月'
        else title = `${date.getFullYear()}年${date.getMonth() + 1}月`
      }
      if (!groups[title]) groups[title] = []
      groups[title].push(video)
    })

    return Object.entries(groups)
      .map(([title, videos]) => ({ title, videos }))
      .sort((a, b) => {
        const ai = BUCKET_ORDER.indexOf(a.title)
        const bi = BUCKET_ORDER.indexOf(b.title)
        // Named buckets sort by their fixed order; year-month buckets (index -1)
        // fall after, preserving their natural string order.
        if (ai !== -1 && bi !== -1) return ai - bi
        if (ai !== -1) return -1
        if (bi !== -1) return 1
        return a.title < b.title ? 1 : a.title > b.title ? -1 : 0
      })
  })

  return { videoGroups }
}
