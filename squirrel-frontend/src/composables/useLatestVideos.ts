import { computed, shallowRef, ref } from 'vue'
import { getVideoList } from '@/api'

type VideoId = string | number

type VideoListItem = {
  id: VideoId
  is_read?: boolean
  isPlaying?: boolean
  video_url?: string | null
  [key: string]: unknown
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
}

type ApiResult<T> = { data?: T | null; error?: unknown | null }
type VideoListResponse = { data?: unknown[] }
type ApiErrorLike = { type?: string | null }
type VideoListParams = {
  page: number
  pageSize: number
  query: string
  subscription_id: VideoId | null
  category: string
  sort_by: string
  nsfw: string
  site: string | undefined
  time_range: string
  duration: string
  content_type: string
}

const PAGE_SIZE = 50

const normalizeVideoListItem = (video: any): VideoListItem => ({
  ...video,
  is_read: video?.is_read ?? false,
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

export default function useLatestVideos(initial: InitialState = {}) {
  const videos = shallowRef<VideoListItem[]>([])
  const loading = ref(false)
  const allLoaded = ref(false)
  const error = ref<unknown | null>(null)
  const activeTab = ref(initial.activeTab ?? 'unread')
  const currentPage = ref(1)
  const searchQuery = ref(initial.searchQuery ?? '')
  const isResetting = ref(false)
  const subscriptionId = ref<VideoId | null>(initial.subscriptionId ?? null)
  const sortBy = ref(initial.sortBy ?? 'publish_date')
  const nsfw = ref(initial.nsfw ?? 'all')
  const site = ref<string | undefined>(initial.site)
  const timeRange = ref(initial.timeRange ?? 'all')
  const duration = ref(initial.duration ?? 'all')
  const contentType = ref(initial.contentType ?? 'all')

  const category = computed(() => activeTab.value)

  let requestToken = 0
  let listAbortController: AbortController | null = null

  const createRequestParams = (): VideoListParams => ({
    page: currentPage.value,
    pageSize: PAGE_SIZE,
    query: searchQuery.value || '',
    subscription_id: subscriptionId.value,
    category: category.value,
    sort_by: sortBy.value,
    nsfw: nsfw.value,
    site: site.value,
    time_range: timeRange.value,
    duration: duration.value,
    content_type: contentType.value,
  })

  const finishRequest = (): void => {
    loading.value = false
  }

  const applyVideoPage = (nextVideos: VideoListItem[], requestedPage: number): void => {
    if (requestedPage === 1) {
      videos.value = dedupeByVideoId(nextVideos)
      return
    }

    videos.value = appendUniqueVideos(videos.value, nextVideos)
  }

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return
    loading.value = true

    const requestPage = currentPage.value
    const currentToken = ++requestToken
    listAbortController?.abort()
    listAbortController = new AbortController()

    const { data, error: requestError } = (await getVideoList(createRequestParams(), {
      signal: listAbortController.signal,
    })) as ApiResult<VideoListResponse>

    if (currentToken !== requestToken) {
      finishRequest()
      return
    }

    if ((requestError as ApiErrorLike | null)?.type === 'CANCELED') {
      finishRequest()
      return
    }

    if (requestError) {
      error.value = requestError
      finishRequest()
      return
    }

    const nextVideos = extractVideoListItems(data)
    applyVideoPage(nextVideos, requestPage)

    currentPage.value++
    allLoaded.value = nextVideos.length < PAGE_SIZE
    finishRequest()
  }

  const resetAndReload = async () => {
    isResetting.value = true
    currentPage.value = 1
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
    isResetting,
  }
}
