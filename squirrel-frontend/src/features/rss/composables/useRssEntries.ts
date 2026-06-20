import { computed, ref, watch, type Ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { copyToClipboard } from '@/shared/lib/clipboard'
import { useContextMenuPosition } from '@/shared/composables/useContextMenuPosition'
import {
  getRssEntries,
  getRssRecentlyViewed,
  recordRssEntryView,
  updateRssEntries,
  updateRssEntry,
} from '@/shared/api'
import type { RssEntry, RssFeed, RecentEntry, ReadBatchMode } from './rssTypes'

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
  const contextMenuRef = ref<HTMLElement | null>(null)
  const { position: contextMenuPosition, positionMenu } = useContextMenuPosition()
  const contextMenuEntry = ref<RssEntry | null>(null)

  const feedNavStack = ref<{
    selectedFeedId: number | null
    activeFilter: 'all' | 'unread' | 'starred' | 'recent'
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
    try {
      const data = await getRssRecentlyViewed()
      recentlyViewed.value = data?.data || []
    } catch {
      // silent — recently-viewed is a secondary list
    }
  }

  // Shared query builder + fetch for loadEntries/loadMore. Returns null on
  // error (already reported via onStatus) so callers can early-return.
  const buildEntriesParams = (): Record<string, unknown> => {
    const params: Record<string, unknown> = { page: page.value, pageSize: pageSize.value }
    if (options.selectedAccountId.value) params.accountId = options.selectedAccountId.value
    if (options.selectedFeedId.value) params.feedId = options.selectedFeedId.value
    if (activeFilter.value === 'unread') {
      params.isRead = false
    } else if (activeFilter.value === 'starred') {
      params.isStarred = true
    }
    return params
  }

  const fetchEntriesPage = async (): Promise<{ fetched: RssEntry[]; total: number } | null> => {
    try {
      const data = await getRssEntries(buildEntriesParams())
      return { fetched: data?.data || [], total: data?.total || 0 }
    } catch (err) {
      options?.onStatus?.(errorMessage(err, '加载文章失败'), true)
      return null
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

    const result = await fetchEntriesPage()
    if (!result) return

    totalEntries.value = result.total
    entries.value = isReset ? result.fetched : [...entries.value, ...result.fetched]
  }

  const loadMore = async () => {
    if (loadingMoreEntries.value || !hasMoreEntries.value) return
    page.value += 1
    loadingMoreEntries.value = true

    const result = await fetchEntriesPage()
    loadingMoreEntries.value = false
    if (!result) return

    totalEntries.value = result.total
    const existingIds = new Set(entries.value.map((entry) => String(entry.id)))
    entries.value.push(...result.fetched.filter((entry) => !existingIds.has(String(entry.id))))
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
    activeFilter.value = stack.activeFilter
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
    try {
      await updateRssEntry(entry.id, { isRead: newStatus })
      if (reloadFilteredList && shouldReloadAfterEntryUpdate(entry)) {
        await loadEntries(true)
      }
    } catch (err) {
      // rollback optimistic update
      entry.is_read = !newStatus
      if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
        options.readingEntry.value.is_read = !newStatus
      }
      options?.onStatus?.(errorMessage(err, '更新失败'), true)
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
    try {
      const data = await updateRssEntries({
        entryIds: targets.map((entry) => entry.id),
        isRead,
      })
      options?.onStatus?.(`已更新 ${data?.updated ?? targets.length} 篇文章`)
      if (activeFilter.value === 'unread' && isRead) {
        totalEntries.value = Math.max(0, totalEntries.value - targets.length)
        page.value = 0
      }
    } catch (err) {
      previous.forEach(({ entry, isRead: previousIsRead }) => {
        entry.is_read = previousIsRead
        if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
          options.readingEntry.value.is_read = previousIsRead
        }
      })
      options?.onStatus?.(errorMessage(err, '批量更新失败'), true)
    }
  }

  const toggleStarStatus = async (entry: RssEntry) => {
    const newStatus = !entry.is_starred
    entry.is_starred = newStatus
    if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
      options.readingEntry.value.is_starred = newStatus
    }
    try {
      await updateRssEntry(entry.id, { isStarred: newStatus })
      options?.onStatus?.(newStatus ? '已收藏' : '已取消收藏')
    } catch (err) {
      entry.is_starred = !newStatus
      if (options.readingEntry?.value && String(options.readingEntry.value.id) === String(entry.id)) {
        options.readingEntry.value.is_starred = !newStatus
      }
      options?.onStatus?.(errorMessage(err, '收藏失败'), true)
    }
  }

  const showArticleContextMenu = (entry: RssEntry, event: MouseEvent) => {
    contextMenuEntry.value = entry
    positionMenu(event, contextMenuRef)
    showContextMenu.value = true
  }

  const closeContextMenu = () => {
    showContextMenu.value = false
    contextMenuEntry.value = null
  }

  const copyArticleLink = async (entry: RssEntry) => {
    const ok = await copyToClipboard(entry.canonical_url)
    options?.onStatus?.(ok ? '已成功复制链接到剪贴板' : '复制链接失败', !ok)
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
