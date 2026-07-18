import { afterEach, describe, expect, it, vi } from 'vitest'
import { ref } from 'vue'
import type { VideoListItem } from '@/features/video/types/video'
import { useFeedGrouping } from './useFeedGrouping'

describe('useFeedGrouping', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('keeps undated records visible in a final date bucket', () => {
    vi.useFakeTimers()
    const now = new Date(2026, 6, 18, 12)
    vi.setSystemTime(now)

    const feedItems = ref([
      {
        id: 1,
        title: '今天入库',
        url: 'https://example.com/today',
        thumbnail: null,
        duration: null,
        last_position: 0,
        uploaded_at: new Date(2026, 6, 18, 9).toISOString(),
        created_at: new Date(2026, 6, 18, 10).toISOString(),
        subscriptions: [],
        actors: [],
      },
      {
        id: 2,
        title: '日期缺失',
        url: 'https://example.com/undated',
        thumbnail: null,
        duration: null,
        last_position: 0,
        uploaded_at: null,
        created_at: '',
        subscriptions: [],
        actors: [],
      },
    ] satisfies VideoListItem[])

    const { videoGroups } = useFeedGrouping({ feedItems })

    expect(videoGroups.value.map((group) => group.title)).toEqual(['今天', '日期未明'])
    expect(videoGroups.value[1]?.videos.map((video) => video.id)).toEqual([2])
  })
})
