import { computed, onScopeDispose, ref, watch, type Ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { copyToClipboard } from '@/shared/lib/clipboard'
import { openExternalUrl } from '@/shared/lib/externalUrl'
import { useContextMenuPosition } from '@/shared/composables/useContextMenuPosition'
import {
  getRssEntries,
  getRssRecentlyViewed,
  recordRssEntryView,
  updateRssEntries,
  updateRssEntry,
} from '@/shared/api'
import type { RssEntry, RssFeed, RecentEntry, ReadBatchMode } from '@/features/rss/types/rss'

// 单次 push 之前的状态快照。当用户从「全部/筛选列表」跳进某个 feed
// （通过右键菜单"查看该源"、或在阅读面板点订阅源名字），需要把
// 上一次的 selectedFeedId / activeFilter / page / 已加载 entries /
// totalEntries / readingEntry 保存下来，"返回"时还原。
//
// 实现是栈：连续多次「跳到 feed」中间不丢状态；栈空时返回按钮自动消失。
// 上层 (RssSources.vue) 通过 useNavigationHistory.registerInternalBackHandler
// 把「出栈」接进应用导航，让鼠标、Alt+← 和快捷键行为一致。
export interface FeedNavSnapshot {
  selectedFeedId: number | null
  activeFilter: 'all' | 'unread' | 'starred' | 'recent'
  page: number
  entries: RssEntry[]
  totalEntries: number
  readingEntry: RssEntry | null
}

type EntriesPageResult =
  | { ok: true; fetched: RssEntry[]; total: number }
  | { ok: false; error: string }

export function useRssEntries(options: {
  selectedAccountId: Ref<number | null>
  selectedFeedId: Ref<number | null>
  feeds: Ref<RssFeed[]>
  searchQuery: Readonly<Ref<string>>
  searchTrigger: Readonly<Ref<number>>
  getFeedTitle: (feedId: number) => string
  readingEntry?: Ref<RssEntry | null>
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const entries = ref<RssEntry[]>([])
  const activeFilter = ref<'all' | 'unread' | 'starred' | 'recent'>('all')
  const page = ref(1)
  const pageSize = ref(30)
  const totalEntries = ref(0)
  const loadingEntries = ref(true)
  const loadingMoreEntries = ref(false)
  const entriesError = ref('')
  const recentlyViewed = ref<RecentEntry[]>([])
  const entriesContainer = ref<HTMLElement | null>(null)
  const loadMoreTrigger = ref<HTMLElement | null>(null)
  let entriesObserver: IntersectionObserver | null = null
  let entriesRequestToken = 0
  let recentRequestToken = 0

  // Context Menu States
  const showContextMenu = ref(false)
  const contextMenuRef = ref<HTMLElement | null>(null)
  const { position: contextMenuPosition, positionMenu } = useContextMenuPosition()
  const contextMenuEntry = ref<RssEntry | null>(null)

  const feedNavStack = ref<FeedNavSnapshot[]>([])
  let searchTimer: ReturnType<typeof setTimeout> | undefined

  const hasFeedNavStack = computed(() => feedNavStack.value.length > 0)

  const hasMoreEntries = computed(() => {
    if (loadingEntries.value || activeFilter.value === 'recent') return false
    return entries.value.length < totalEntries.value
  })

  const filteredEntries = computed(() => {
    if (activeFilter.value === 'recent') {
      let list = recentlyViewed.value
      const query = options.searchQuery.value.trim().toLowerCase()
      if (query) {
        list = list.filter((entry) => {
          return entry.title.toLowerCase().includes(query) ||
            (entry.summary ? entry.summary.toLowerCase().includes(query) : false)
        })
      }
      return list
    }
    return entries.value
  })

  const resetScroll = () => {
    if (entriesContainer.value) {
      entriesContainer.value.scrollTop = 0
    }
  }

  const loadRecentlyViewed = async () => {
    const accountId = options.selectedAccountId.value
    const requestToken = ++recentRequestToken
    if (!accountId) {
      recentlyViewed.value = []
      return
    }
    try {
      const data = await getRssRecentlyViewed(accountId)
      if (requestToken !== recentRequestToken || options.selectedAccountId.value !== accountId) return
      recentlyViewed.value = data?.data || []
    } catch (err) {
      if (requestToken !== recentRequestToken || options.selectedAccountId.value !== accountId) return
      recentlyViewed.value = []
      entriesError.value = errorMessage(err, '加载最近浏览失败')
      options?.onStatus?.(entriesError.value, true)
    }
  }

  const buildEntriesParams = (accountId: number): Record<string, unknown> => {
    const params: Record<string, unknown> = {
      accountId,
      page: page.value,
      pageSize: pageSize.value,
    }
    if (options.selectedFeedId.value) params.feedId = options.selectedFeedId.value
    if (activeFilter.value === 'unread') {
      params.isRead = false
    } else if (activeFilter.value === 'starred') {
      params.isStarred = true
    }
    const query = options.searchQuery.value.trim()
    if (query) params.query = query
    return params
  }

  // Fetching is intentionally side-effect free. The caller owns request
  // identity and may commit the result only while its account is still active.
  const fetchEntriesPage = async (params: Record<string, unknown>): Promise<EntriesPageResult> => {
    try {
      const data = await getRssEntries(params)
      return { ok: true, fetched: data?.data || [], total: data?.total || 0 }
    } catch (err) {
      return { ok: false, error: errorMessage(err, '加载文章失败') }
    }
  }

  const isCurrentEntriesRequest = (requestToken: number, accountId: number) => {
    return requestToken === entriesRequestToken && options.selectedAccountId.value === accountId
  }

  const reportEntriesError = (message: string) => {
    if (entries.value.length === 0) entriesError.value = message
    options.onStatus?.(message, true)
  }

  const loadEntries = async (isReset = false) => {
    const requestToken = ++entriesRequestToken
    const accountId = options.selectedAccountId.value

    if (isReset) {
      page.value = 1
      entries.value = []
      totalEntries.value = 0
      loadingEntries.value = true
      loadingMoreEntries.value = false
      entriesError.value = ''
      resetScroll()
    }

    if (!accountId) {
      recentRequestToken += 1
      recentlyViewed.value = []
      loadingEntries.value = false
      return
    }

    if (activeFilter.value === 'recent') {
      await loadRecentlyViewed()
      if (!isCurrentEntriesRequest(requestToken, accountId)) return
      loadingEntries.value = false
      return
    }

    const result = await fetchEntriesPage(buildEntriesParams(accountId))
    if (!isCurrentEntriesRequest(requestToken, accountId)) return
    loadingEntries.value = false
    if (!result.ok) {
      reportEntriesError(result.error)
      return
    }

    totalEntries.value = result.total
    entries.value = isReset ? result.fetched : [...entries.value, ...result.fetched]
  }

  const loadMore = async () => {
    if (loadingEntries.value || loadingMoreEntries.value || !hasMoreEntries.value) return
    const requestToken = ++entriesRequestToken
    const accountId = options.selectedAccountId.value
    if (!accountId) return
    const previousPage = page.value
    page.value = previousPage + 1
    loadingMoreEntries.value = true

    const result = await fetchEntriesPage(buildEntriesParams(accountId))
    if (!isCurrentEntriesRequest(requestToken, accountId)) return
    loadingMoreEntries.value = false
    if (!result.ok) {
      page.value = previousPage
      reportEntriesError(result.error)
      return
    }

    totalEntries.value = result.total
    const existingIds = new Set(entries.value.map((entry) => String(entry.id)))
    entries.value.push(...result.fetched.filter((entry) => !existingIds.has(String(entry.id))))
  }

  const recordRecentlyViewed = (entry: RssEntry) => {
    void recordRssEntryView(entry.id).catch((err) => {
      options?.onStatus?.(errorMessage(err, '记录浏览历史失败'), true)
    })
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
    const alreadyShowingAll = activeFilter.value === 'all'
    activeFilter.value = 'all'
    if (alreadyShowingAll) await loadEntries(true)
  }

  const pushFeedNavStack = () => {
    feedNavStack.value.push({
      selectedFeedId: options.selectedFeedId.value,
      activeFilter: activeFilter.value,
      page: page.value,
      entries: [...entries.value],
      totalEntries: totalEntries.value,
      readingEntry: options.readingEntry?.value ?? null,
    })
  }

  const goBackFromFeed = (): boolean => {
    const stack = feedNavStack.value
    const snapshot = stack.pop()
    if (!snapshot) return false
    options.selectedFeedId.value = snapshot.selectedFeedId
    activeFilter.value = snapshot.activeFilter
    page.value = snapshot.page
    entries.value = snapshot.entries
    totalEntries.value = snapshot.totalEntries
    if (options.readingEntry) {
      options.readingEntry.value = snapshot.readingEntry
    }
    resetScroll()
    return true
  }

  // 仅清空栈、不做还原。给 unmount / 显式 reset 用。
  const clearFeedNavStack = () => {
    feedNavStack.value = []
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
        await loadEntries(true)
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
      if (shouldReloadAfterEntryUpdate(entry)) {
        await loadEntries(true)
      }
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
    void openExternalUrl(entry.canonical_url)
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

  watch(options.searchQuery, () => {
    if (activeFilter.value === 'recent') return
    entriesRequestToken += 1
    clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      loadEntries(true)
    }, 250)
  })

  watch(options.searchTrigger, () => {
    if (activeFilter.value === 'recent') return
    clearTimeout(searchTimer)
    loadEntries(true)
  })

  onScopeDispose(() => {
    clearTimeout(searchTimer)
    entriesObserver?.disconnect()
    entriesObserver = null
    entriesRequestToken += 1
    recentRequestToken += 1
  })

  return {
    entries,
    activeFilter,
    page,
    pageSize,
    totalEntries,
    loadingEntries,
    loadingMoreEntries,
    entriesError,
    recentlyViewed,
    entriesContainer,
    loadMoreTrigger,
    hasFeedNavStack,
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
    clearFeedNavStack,
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
