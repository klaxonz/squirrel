import { computed, shallowRef, ref, watch } from 'vue'
import { getVideoCounts, getVideoList } from '@/api'

type VideoId = string | number

type VideoListItem = {
  id: VideoId
  is_read?: boolean
  isPlaying?: boolean
  video_url?: string | null
  [key: string]: unknown
}

type VideoCounts = {
  all: number
  unread: number
  read: number
  preview: number
  liked: number
  later: number
  [key: string]: number
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

export default function useLatestVideos(initial: InitialState = {}) {
  const videos = shallowRef<VideoListItem[]>([])
  const loading = ref(false)
  const allLoaded = ref(false)
  const error = ref<unknown | null>(null)
  const activeTab = ref(initial.activeTab ?? 'unread')
  const videoCounts = ref<VideoCounts>({ all: 0, unread: 0, read: 0, preview: 0, liked: 0, later: 0 })
  const countsLoading = ref(false)
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
  let countsRequestToken = 0

  const loadVideoCounts = async () => {
    countsLoading.value = true
    const currentToken = ++countsRequestToken

    const { data, error: requestError } = (await getVideoCounts({
      query: searchQuery.value || '',
      subscription_id: subscriptionId.value,
      nsfw: nsfw.value,
      site: site.value,
      time_range: timeRange.value,
      duration: duration.value,
      content_type: contentType.value,
    })) as ApiResult<VideoCounts>

    if (currentToken !== countsRequestToken) {
      countsLoading.value = false
      return null
    }

    if (!requestError && data) {
      videoCounts.value = data
    }

    countsLoading.value = false
    return data ?? null
  }

  const loadMore = async () => {
    if (loading.value || allLoaded.value) return
    loading.value = true

    const pageSize = 50
    const currentToken = ++requestToken

    const { data, error: requestError } = (await getVideoList({
      page: currentPage.value,
      pageSize,
      query: searchQuery.value || '',
      subscription_id: subscriptionId.value,
      category: category.value,
      sort_by: sortBy.value,
      nsfw: nsfw.value,
      site: site.value,
      time_range: timeRange.value,
      duration: duration.value,
      content_type: contentType.value,
    })) as ApiResult<VideoListResponse>

    if (currentToken !== requestToken) {
      loading.value = false
      return
    }

    if (requestError) {
      error.value = requestError
      loading.value = false
      return
    }

    const rawList = Array.isArray(data?.data) ? data?.data : []
    const newVideos: VideoListItem[] = rawList.map((video: any) => ({
      ...video,
      is_read: video?.is_read ?? false,
      isPlaying: false,
      video_url: null,
    }))

    if (currentPage.value === 1) {
      const seen = new Set<VideoId>()
      const deduped = newVideos.filter((video) => {
        if (seen.has(video.id)) return false
        seen.add(video.id)
        return true
      })
      videos.value = deduped
    } else {
      const existingIds = new Set(videos.value.map((v) => v.id))
      const uniqueNewVideos = newVideos.filter((video) => !existingIds.has(video.id))
      videos.value = [...videos.value, ...uniqueNewVideos]
    }

    currentPage.value++
    allLoaded.value = newVideos.length < pageSize
    loading.value = false

    if (currentPage.value === 2) {
      loadVideoCounts()
    }
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

  watch([subscriptionId, searchQuery, nsfw, site, timeRange, duration, contentType], () => {
    if (currentPage.value > 1) {
      loadVideoCounts()
    }
  })

  return {
    videos,
    loading,
    allLoaded,
    error,
    activeTab,
    videoCounts,
    countsLoading,
    handleSearch: resetAndReload,
    refresh: resetAndReload,
    loadMore,
    loadVideoCounts,
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
