import { computed, nextTick, ref, watch, type Ref } from 'vue'
import {
  getRssEntries,
  getRssRecentlyViewed,
  recordRssEntryView,
  updateRssEntries,
  updateRssEntry,
} from '@/api'
import type { ApiResult, RssEntry, RssFeed, RecentEntry, ReadBatchMode } from './rssTypes'

export function useRssEntries(options: {
  selectedAccountId: Ref<number | null>
  selectedFeedId: Ref<number | null>
  feeds: Ref<RssFeed[]>
  getFeedTitle: (feedId: number) => string
  readingEntry?: Ref<RssEntry | null>
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const entries = ref<RssEntry[]>([])
  const activeFilter = ref<'all' | 'unread' | 'starred' | 'recent'>('unread')
  const entrySearch = ref('')
  const page = ref(1)
  const pageSize = ref(30)
  const totalEntries = ref(0)
  const loadingMoreEntries = ref(false)
  const recentlyViewed = ref<RecentEntry[]>([])
  const entriesContainer = ref<HTMLElement | null>(null)
  const loadMoreTrigger = ref<HTMLElement | null>(null)
  let entriesObserver: IntersectionObserver | null = null

  // Context Menu States
  const showContextMenu = ref(false)
  const contextMenuPosition = ref({ x: 0, y: 0 })
  const contextMenuEntry = ref<RssEntry | null>(null)
  const contextMenuRef = ref<HTMLElement | null>(null)

  const feedNavStack = ref<{
    selectedFeedId: number | null
    activeFilter: string
    page: number
    entries: RssEntry[]
    totalEntries: number
    readingEntry: RssEntry | null
  } | null>(null)

  const hasMoreEntries = computed(() => {
    if (activeFilter.value === 'recent') return false
    return entries.value.length < totalEntries.value
  })

  const filteredEntries = computed(() => {
    if (activeFilter.value === 'recent') {
      let list = recentlyViewed.value
      const query = entrySearch.value.trim().toLowerCase()
      if (query) {
        list = list.filter((entry) => {
          return entry.title.toLowerCase().includes(query) ||
            (entry.summary ? entry.summary.toLowerCase().includes(query) : false)
        })
      }
      return list
    }
    let list = entries.value
    const query = entrySearch.value.trim().toLowerCase()
    if (query) {
      list = list.filter((entry) => {
        return entry.title.toLowerCase().includes(query) ||
          (entry.summary ? entry.summary.toLowerCase().includes(query) : false)
      })
    }
    return list
  })

  const resetScroll = () => {
    if (entriesContainer.value) {
      entriesContainer.value.scrollTop = 0
    }
  }

  const loadRecentlyViewed = async () => {
    const result = await getRssRecentlyViewed() as ApiResult<{ data: RecentEntry[] }>
    if (!result.error) {
      recentlyViewed.value = result.data?.data || []
    }
  }

  const loadEntries = async (isReset = false) => {
    if (activeFilter.value === 'recent') {
      await loadRecentlyViewed()
      if (isReset) resetScroll()
      return
    }
    if (isReset) {
      page.value = 1
      entries.value = []
      resetScroll()
    }
    const params: Record<string, unknown> = { page: page.value, pageSize: pageSize.value }
    if (options.selectedAccountId.value) params.accountId = options.selectedAccountId.value
    if (options.selectedFeedId.value) params.feedId = options.selectedFeedId.value
    if (activeFilter.value === 'unread') {
      params.isRead = false
    } else if (activeFilter.value === 'starred') {
      params.isStarred = true
    }

    const result = await getRssEntries(params) as ApiResult<{ data: RssEntry[], total: number }>
    if (result.error) {
      options?.onStatus?.((result.error as { message?: string })?.message || '加载条目失败', true)
      return
    }

    const fetched = result.data?.data || []
    totalEntries.value = (result.data as any)?.total || 0

    if (isReset) {
      entries.value = fetched
    } else {
      entries.value.push(...fetched)
    }
  }

  const loadMore = async () => {
    if (loadingMoreEntries.value || !hasMoreEntries.value) return
    page.value += 1
    loadingMoreEntries.value = true
    const params: Record<string, unknown> = { page: page.value, pageSize: pageSize.value }
    if (options.selectedAccountId.value) params.accountId = options.selectedAccountId.value
    if (options.selectedFeedId.value) params.feedId = options.selectedFeedId.value
    if (activeFilter.value === 'unread') {
      params.isRead = false
    } else if (activeFilter.value === 'starred') {
      params.isStarred = true
    }

    const result = await getRssEntries(params) as ApiResult<{ data: RssEntry[], total: number }>
    loadingMoreEntries.value = false
    if (result.error) {
      options?.onStatus?.((result.error as { message?: string })?.message || '加载条目失败', true)
      return
    }
    const fetched = result.data?.data || []
    totalEntries.value = (result.data as any)?.total || 0
    entries.value.push(...fetched)
  }

  const recordRecentlyViewed = (entry: RssEntry) => {
    recordRssEntryView(entry.id)
    const recent: RecentEntry = {
      ...entry,
      viewed_at: new Date().toISOString(),
    }
    const idx = recentlyViewed.value.findIndex((e) => String(e.id) === String(entry.id))
    if (idx !== -1) {
      recentlyViewed.value.splice(idx, 1)
    }
    recentlyViewed.value.unshift(recent)
  }

  const goToFeedFromContextMenu = async (entry: RssEntry) => {
    closeContextMenu()
    pushFeedNavStack()
    options.selectedFeedId.value = entry.feed_id
    await loadEntries(true)
  }

  const pushFeedNavStack = () => {
    feedNavStack.value = {
      selectedFeedId: options.selectedFeedId.value,
      activeFilter: activeFilter.value,
      page: page.value,
      entries: [...entries.value],
      totalEntries: totalEntries.value,
      readingEntry: options.readingEntry?.value ?? null,
    }
  }

  const goBackFromFeed = () => {
    const stack = feedNavStack.value
    if (!stack) return
    options.selectedFeedId.value = stack.selectedFeedId
    activeFilter.value = stack.activeFilter as any
    page.value = stack.page
    entries.value = stack.entries
    totalEntries.value = stack.totalEntries
    if (options.readingEntry) {
      options.readingEntry.value = stack.readingEntry
    }
    feedNavStack.value = null
    resetScroll()
  }

  const shouldReloadAfterEntryUpdate = (entry: RssEntry) => {
    if (activeFilter.value === 'unread') {
      return entry.is_read
    }
    if (activeFilter.value === 'starred') {
      return !entry.is_starred
    }
    return false
  }

  const toggleReadStatus = async (entry: RssEntry, reloadFilteredList = true) => {
    const newStatus = !entry.is_read
    entry.is_read = newStatus
    if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
      options.readingEntry.value.is_read = newStatus
    }
    const result = await updateRssEntry(entry.id, { isRead: newStatus })
    if (result.error) {
      entry.is_read = !newStatus
      if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
        options.readingEntry.value.is_read = !newStatus
      }
      options?.onStatus?.((result.error as { message?: string })?.message || '更新已读状态失败', true)
      return
    }
    if (reloadFilteredList && shouldReloadAfterEntryUpdate(entry)) {
      await loadEntries(true)
    }
  }

  const getBatchReadTargets = (mode: ReadBatchMode) => {
    if (!contextMenuEntry.value) return []
    const list = filteredEntries.value
    if (mode === 'all') return list
    const index = list.findIndex((entry) => String(entry.id) === String(contextMenuEntry.value?.id))
    if (index < 0) return []
    if (mode === 'above') return list.slice(0, index)
    return list.slice(index + 1)
  }

  const batchUpdateReadStatus = async (mode: ReadBatchMode, isRead: boolean) => {
    const targets = getBatchReadTargets(mode).filter((entry) => entry.is_read !== isRead)
    if (targets.length === 0) {
      options?.onStatus?.('没有需要更新的文章')
      return
    }
    const previous = targets.map((entry) => ({ entry, isRead: entry.is_read }))
    targets.forEach((entry) => {
      entry.is_read = isRead
      if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
        options.readingEntry.value.is_read = isRead
      }
    })
    const result = await updateRssEntries({
      entryIds: targets.map((entry) => entry.id),
      isRead,
    }) as ApiResult<{ updated: number }>
    if (result.error) {
      previous.forEach(({ entry, isRead: previousIsRead }) => {
        entry.is_read = previousIsRead
        if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
          options.readingEntry.value.is_read = previousIsRead
        }
      })
      options?.onStatus?.((result.error as { message?: string })?.message || '批量更新已读状态失败', true)
      return
    }
    options?.onStatus?.(`已更新 ${result.data?.updated ?? targets.length} 篇文章`)
    if (targets.some(shouldReloadAfterEntryUpdate)) {
      await loadEntries(true)
    }
  }

  const toggleStarStatus = async (entry: RssEntry) => {
    const newStatus = !entry.is_starred
    entry.is_starred = newStatus
    if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
      options.readingEntry.value.is_starred = newStatus
    }
    const result = await updateRssEntry(entry.id, { isStarred: newStatus })
    if (result.error) {
      entry.is_starred = !newStatus
      if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
        options.readingEntry.value.is_starred = !newStatus
      }
      options?.onStatus?.((result.error as { message?: string })?.message || '更新星标状态失败', true)
      return
    }
    options?.onStatus?.(newStatus ? '已收藏' : '已取消收藏')
  }

  const showArticleContextMenu = (entry: RssEntry, event: MouseEvent) => {
    contextMenuEntry.value = entry
    let x = event.clientX
    let y = event.clientY
    const menuWidth = 200
    if (x + menuWidth > window.innerWidth) {
      x = window.innerWidth - menuWidth - 8
    }
    contextMenuPosition.value = { x, y }
    showContextMenu.value = true
    nextTick(() => {
      const el = contextMenuRef.value
      if (!el) return
      const rect = el.getBoundingClientRect()
      if (rect.bottom > window.innerHeight) {
        contextMenuPosition.value = { x, y: window.innerHeight - rect.height - 8 }
      }
    })
  }

  const closeContextMenu = () => {
    showContextMenu.value = false
    contextMenuEntry.value = null
  }

  const copyArticleLink = async (entry: RssEntry) => {
    try {
      await navigator.clipboard.writeText(entry.canonical_url)
      options?.onStatus?.('已成功复制链接到剪贴板')
    } catch {
      options?.onStatus?.('复制链接失败', true)
    }
  }

  const openInExternalBrowser = (entry: RssEntry) => {
    window.open(entry.canonical_url, '_blank')
  }

  const initObserver = () => {
    entriesObserver?.disconnect()
    entriesObserver = new IntersectionObserver(
      (entriesList) => {
        if (entriesList[0].isIntersecting && hasMoreEntries.value) {
          loadMore()
        }
      },
      {
        root: entriesContainer.value,
        rootMargin: '400px',
      }
    )
    if (loadMoreTrigger.value) {
      entriesObserver.observe(loadMoreTrigger.value)
    }
  }

  watch(activeFilter, () => {
    loadEntries(true)
  })

  return {
    entries,
    activeFilter,
    entrySearch,
    page,
    pageSize,
    totalEntries,
    loadingMoreEntries,
    recentlyViewed,
    entriesContainer,
    loadMoreTrigger,
    feedNavStack,
    showContextMenu,
    contextMenuPosition,
    contextMenuEntry,
    contextMenuRef,
    hasMoreEntries,
    filteredEntries,
    loadEntries,
    loadMore,
    loadRecentlyViewed,
    recordRecentlyViewed,
    resetScroll,
    pushFeedNavStack,
    goBackFromFeed,
    shouldReloadAfterEntryUpdate,
    toggleReadStatus,
    getBatchReadTargets,
    batchUpdateReadStatus,
    toggleStarStatus,
    showArticleContextMenu,
    closeContextMenu,
    copyArticleLink,
    openInExternalBrowser,
    goToFeedFromContextMenu,
    initObserver,
  }
}
