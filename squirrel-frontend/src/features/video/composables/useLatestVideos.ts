import { computed, shallowRef, ref } from 'vue'
import { getVideoList } from '@/shared/api'
import type { VideoListItem as ApiVideoListItem, VideoListResponse as ApiVideoListResponse } from '@/features/video/types/video'
import { ErrorTypes } from '@/shared/lib/request'
import { isApiError } from '@/shared/lib/apiError'

type VideoId = string | number

// Feed video items carry a few local UI-only flags on top of the API shape.
type VideoListItem = ApiVideoListItem & {
  is_read?: boolean
  isPlaying?: boolean
  video_url?: string | null
}

type InitialState = {
  activeTab?: string
  searchQuery?: string
  subscriptionId?: VideoId | null
  sortBy?: string
  nsfw?: string
  site?: string
  timeRange?: string
  duration?: string
  contentType?: string
  special?: string
}

type VideoListResponse = ApiVideoListResponse
type VideoListParams = {
  cursor: string | null
  pageSize: number
  page_size: number
  query: string
  subscription_id: VideoId | null
  category: string
  sort_by: string
  nsfw: string
  site: string | undefined
  time_range: string
  duration: string
  content_type: string
  special: string
}

const PAGE_SIZE = 50

const normalizeVideoListItem = (video: ApiVideoListItem): VideoListItem => ({
  ...video,
  is_read: false,
  isPlaying: false,
  video_url: null,
})

const extractVideoListItems = (payload: VideoListResponse | null | undefined): VideoListItem[] => {
  const rawList = Array.isArray(payload?.data) ? payload.data : []
  return rawList.map((video) => normalizeVideoListItem(video))
}

const dedupeByVideoId = (videos: VideoListItem[]): VideoListItem[] => {
  const seen = new Set<VideoId>()
  return videos.filter((video) => {
    if (seen.has(video.id)) {
      return false
    }
    seen.add(video.id)
    return true
  })
}

const appendUniqueVideos = (currentVideos: VideoListItem[], nextVideos: VideoListItem[]): VideoListItem[] => {
  if (!currentVideos.length) {
    return dedupeByVideoId(nextVideos)
  }

  const existingIds = new Set(currentVideos.map((video) => video.id))
  const uniqueVideos = nextVideos.filter((video) => !existingIds.has(video.id))
  return currentVideos.concat(uniqueVideos)
}

export function useLatestVideos(initial: InitialState = {}) {
  const videos = shallowRef<VideoListItem[]>([])
  const loading = ref(false)
  const allLoaded = ref(false)
  const error = ref<unknown | null>(null)
  // Default to 'all' to match useFeedFilters/VideoTab defaults; 'unread'
  // here would otherwise leak a stale category before the route-derived tab
  // is applied on first render.
  const activeTab = ref(initial.activeTab ?? 'all')
  const cursor = ref<string | null>(null)
  const searchQuery = ref(initial.searchQuery ?? '')
  const isResetting = ref(false)
  const subscriptionId = ref<VideoId | null>(initial.subscriptionId ?? null)
  const sortBy = ref(initial.sortBy ?? 'publish_date')
  const nsfw = ref(initial.nsfw ?? 'all')
  const site = ref<string | undefined>(initial.site)
  const timeRange = ref(initial.timeRange ?? 'all')
  const duration = ref(initial.duration ?? 'all')
  const contentType = ref(initial.contentType ?? 'all')
  const special = ref(initial.special ?? 'all')

  const category = computed(() => activeTab.value)

  let requestToken = 0
  let listAbortController: AbortController | null = null

  const createRequestParams = (): VideoListParams => ({
    cursor: cursor.value,
    pageSize: PAGE_SIZE,
    page_size: PAGE_SIZE,
    query: searchQuery.value || '',
    subscription_id: subscriptionId.value,
    category: category.value,
    sort_by: sortBy.value,
    nsfw: nsfw.value,
    site: site.value,
    time_range: timeRange.value,
    duration: duration.value,
    content_type: contentType.value,
    special: special.value,
  })

  const finishRequest = (): void => {
    loading.value = false
  }

  const applyVideoPage = (nextVideos: VideoListItem[], isRefresh: boolean): void => {
    if (isRefresh) {
      videos.value = dedupeByVideoId(nextVideos)
      return
    }

    videos.value = appendUniqueVideos(videos.value, nextVideos)
  }

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return
    loading.value = true

    const isRefresh = cursor.value === null
    const currentToken = ++requestToken
    listAbortController?.abort()
    listAbortController = new AbortController()

    try {
      const data = await getVideoList(createRequestParams(), {
        signal: listAbortController.signal,
      })

      if (currentToken !== requestToken) {
        finishRequest()
        return
      }

      const nextVideos = extractVideoListItems(data)
      applyVideoPage(nextVideos, isRefresh)

      // 推进游标；后端返回的 next_cursor 为 null 表示无更多
      cursor.value = data?.next_cursor ?? null
      allLoaded.value = nextVideos.length < PAGE_SIZE || !data?.next_cursor
    } catch (requestError) {
      // Aborted by a newer request — not a real error, just drop this response.
      if (currentToken !== requestToken || (isApiError(requestError) && requestError.type === ErrorTypes.CANCELED)) {
        finishRequest()
        return
      }
      error.value = requestError
    } finally {
      finishRequest()
    }
  }

  const resetAndReload = async () => {
    isResetting.value = true
    cursor.value = null
    allLoaded.value = false
    error.value = null
    try {
      await loadMore()
    } finally {
      isResetting.value = false
    }
  }

  return {
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    handleSearch: resetAndReload,
    refresh: resetAndReload,
    loadMore,
    searchQuery,
    subscriptionId,
    sortBy,
    nsfw,
    site,
    timeRange,
    duration,
    contentType,
    special,
    isResetting,
  }
}
