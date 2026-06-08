import { computed, nextTick, ref, type Ref } from 'vue'
import { onClickOutside } from '@vueuse/core'
import {
  getRssFeeds,
  markRssFeedAsRead,
  subscribeRssFeed,
  syncRssFeed,
  unsubscribeRssFeed,
  updateRssFeed,
} from '@/api'
import type { ApiResult, RssEntry, RssFeed } from './rssTypes'

export function useRssFeeds(options: {
  selectedAccountId: Ref<number | null>
  onRefreshEntries?: (isReset?: boolean) => Promise<void>
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const feeds = ref<RssFeed[]>([])
  const selectedFeedId = ref<number | null>(null)

  const showSubscribeModal = ref(false)
  const subscribingFeed = ref(false)
  const showCategoryDropdown = ref(false)
  const showCustomCategoryInput = ref(false)
  const customCategoryInputRef = ref<HTMLElement | null>(null)
  const categoryDropdownRef = ref<HTMLElement | null>(null)

  const subscribeForm = ref({
    feedUrl: '',
    category: '',
    customCategory: '',
  })
  const subscribeMessage = ref('')
  const subscribeError = ref(false)

  const feedSearch = ref('')
  const collapsedFolders = ref<Record<string, boolean>>({})

  const showFeedContextMenuState = ref(false)
  const feedContextMenuRef = ref<HTMLElement | null>(null)
  const feedContextMenuPosition = ref({ x: 0, y: 0 })
  const contextMenuFeed = ref<RssFeed | null>(null)

  onClickOutside(categoryDropdownRef, () => {
    showCategoryDropdown.value = false
  })

  const filteredFeeds = computed(() => {
    if (!options.selectedAccountId.value) return feeds.value
    return feeds.value.filter((feed) => feed.account_id === options.selectedAccountId.value)
  })

  const existingCategories = computed(() => {
    const cats = new Set<string>()
    const targetAccountId = options.selectedAccountId.value
    feeds.value.forEach((f) => {
      if (f.account_id === targetAccountId && f.category) {
        cats.add(f.category)
      }
    })
    return [...cats].sort()
  })

  const feedFolders = computed(() => {
    const groups: Record<string, RssFeed[]> = {}
    const query = feedSearch.value.trim().toLowerCase()
    const feedsToGroup = filteredFeeds.value.filter((feed) => {
      if (!query) return true
      return feed.title.toLowerCase().includes(query) ||
        (feed.feed_url && feed.feed_url.toLowerCase().includes(query)) ||
        (feed.category && feed.category.toLowerCase().includes(query))
    })

    feedsToGroup.forEach((feed) => {
      const cat = feed.category || '未分类'
      if (!groups[cat]) groups[cat] = []
      groups[cat].push(feed)
    })

    return Object.entries(groups).map(([name, feeds]) => ({ name, feeds }))
  })

  const loadFeeds = async () => {
    const response = await getRssFeeds(
      options.selectedAccountId.value ? { accountId: options.selectedAccountId.value } : {}
    ) as ApiResult<{ data: RssFeed[] }>
    if (response.error) {
      options?.onStatus?.((response.error as { message?: string })?.message || '加载 Feed 失败', true)
      return
    }
    feeds.value = response.data?.data || []
  }

  const confirmCustomCategory = () => {
    const name = subscribeForm.value.customCategory.trim()
    if (name) {
      subscribeForm.value.category = name
    }
    showCustomCategoryInput.value = false
    showCategoryDropdown.value = false
  }

  const closeSubscribeModal = () => {
    showSubscribeModal.value = false
    showCategoryDropdown.value = false
    showCustomCategoryInput.value = false
    subscribeForm.value = { feedUrl: '', category: '', customCategory: '' }
    subscribeMessage.value = ''
    subscribeError.value = false
  }

  const handleSubscribeFeed = async () => {
    if (!options.selectedAccountId.value || !subscribeForm.value.feedUrl.trim()) return
    subscribingFeed.value = true
    subscribeMessage.value = ''
    subscribeError.value = false

    const response = await subscribeRssFeed({
      accountId: options.selectedAccountId.value,
      feedUrl: subscribeForm.value.feedUrl.trim(),
      category: subscribeForm.value.category.trim() || undefined,
    })

    subscribingFeed.value = false

    if (response.error) {
      subscribeError.value = true
      subscribeMessage.value = (response.error as { message?: string })?.message || '订阅失败'
      return
    }

    subscribeMessage.value = '订阅成功'
    setTimeout(() => {
      closeSubscribeModal()
      loadFeeds()
      options?.onRefreshEntries?.(true)
    }, 1000)
  }

  const toggleFolder = (name: string) => {
    collapsedFolders.value[name] = !collapsedFolders.value[name]
  }

  const selectFeed = async (feedId: number) => {
    selectedFeedId.value = selectedFeedId.value === feedId ? null : feedId
    await options?.onRefreshEntries?.(true)
  }

  const findFeedByEntry = (entryOrFeedId: RssEntry | number): RssFeed | undefined => {
    const feedId = typeof entryOrFeedId === 'number' ? entryOrFeedId : entryOrFeedId.feed_id
    return feeds.value.find((f) => f.id === feedId)
  }

  const getFeedTitle = (feedId: number) => {
    const feed = feeds.value.find((f) => f.id === feedId)
    return feed ? feed.title : '未知源'
  }

  const getFeedCategory = (feedId: number) => {
    const feed = feeds.value.find((f) => f.id === feedId)
    return feed ? feed.category || '未分类' : '未分类'
  }

  const getFeedIconUrl = (feedId: number) => {
    const feed = feeds.value.find((f) => f.id === feedId)
    return feed?.icon_url || null
  }

  const handleUnsubscribeFeed = async (feed: RssFeed) => {
    if (!options.selectedAccountId.value) return
    const response = await unsubscribeRssFeed(feed.id, options.selectedAccountId.value)
    if (response.error) {
      options?.onStatus?.((response.error as { message?: string })?.message || '取消订阅失败', true)
      return
    }
    if (selectedFeedId.value === feed.id) {
      selectedFeedId.value = null
    }
    options?.onStatus?.(`已取消订阅「${feed.title}」`)
    await loadFeeds()
    await options?.onRefreshEntries?.(true)
  }

  const showFeedContextMenu = (feed: RssFeed, event: MouseEvent) => {
    contextMenuFeed.value = feed
    let x = event.clientX
    let y = event.clientY
    const menuWidth = 200
    if (x + menuWidth > window.innerWidth) {
      x = window.innerWidth - menuWidth - 8
    }
    feedContextMenuPosition.value = { x, y }
    showFeedContextMenuState.value = true
    nextTick(() => {
      const el = feedContextMenuRef.value
      if (!el) return
      const rect = el.getBoundingClientRect()
      if (rect.bottom > window.innerHeight) {
        feedContextMenuPosition.value = { x, y: window.innerHeight - rect.height - 8 }
      }
    })
  }

  const closeFeedContextMenu = () => {
    showFeedContextMenuState.value = false
    contextMenuFeed.value = null
  }

  const setFeedOpenMethod = async (feed: RssFeed, method: string | null) => {
    const response = await updateRssFeed(feed.id, { open_method: method }) as ApiResult
    if (response.error) {
      options?.onStatus?.((response.error as { message?: string })?.message || '更新失败', true)
      return
    }
    feed.open_method = method
    closeFeedContextMenu()
    options?.onStatus?.(
      method === 'external_browser'
        ? '已设为系统浏览器打开'
        : method === 'app_browser'
          ? '已设为应用内浏览器打开'
          : '已设为内嵌阅读'
    )
  }

  const syncFeedFromContextMenu = async (feed: RssFeed) => {
    closeFeedContextMenu()
    const response = await syncRssFeed(feed.id) as ApiResult
    if (response.error) {
      options?.onStatus?.((response.error as { message?: string })?.message || '同步失败', true)
      return
    }
    const count = response.data?.entries ?? 0
    options?.onStatus?.(`已同步「${feed.title}」，更新 ${count} 篇文章`)
    await options?.onRefreshEntries?.(true)
  }

  const markFeedAllAsRead = async (feed: RssFeed) => {
    closeFeedContextMenu()
    const response = await markRssFeedAsRead(feed.id) as ApiResult
    if (response.error) {
      options?.onStatus?.((response.error as { message?: string })?.message || '标记已读失败', true)
      return
    }
    options?.onStatus?.(`已将「${feed.title}」全部文章标记为已读`)
    await options?.onRefreshEntries?.(true)
  }

  const copyFeedLink = async (feed: RssFeed) => {
    closeFeedContextMenu()
    if (!feed.feed_url) {
      options?.onStatus?.('订阅源地址为空', true)
      return
    }
    try {
      await navigator.clipboard.writeText(feed.feed_url)
      options?.onStatus?.('已成功复制订阅源地址到剪贴板')
    } catch {
      options?.onStatus?.('复制链接失败', true)
    }
  }

  const openFeedSiteInExternalBrowser = (feed: RssFeed) => {
    closeFeedContextMenu()
    if (feed.site_url) {
      window.open(feed.site_url, '_blank')
    }
  }

  const unsubscribeFeedFromContextMenu = (feed: RssFeed) => {
    closeFeedContextMenu()
    handleUnsubscribeFeed(feed)
  }

  return {
    feeds,
    selectedFeedId,
    showSubscribeModal,
    subscribingFeed,
    showCategoryDropdown,
    showCustomCategoryInput,
    customCategoryInputRef,
    categoryDropdownRef,
    subscribeForm,
    subscribeMessage,
    subscribeError,
    feedSearch,
    collapsedFolders,
    showFeedContextMenuState,
    feedContextMenuRef,
    feedContextMenuPosition,
    contextMenuFeed,
    filteredFeeds,
    existingCategories,
    feedFolders,
    loadFeeds,
    confirmCustomCategory,
    closeSubscribeModal,
    handleSubscribeFeed,
    toggleFolder,
    selectFeed,
    findFeedByEntry,
    getFeedTitle,
    getFeedCategory,
    getFeedIconUrl,
    handleUnsubscribeFeed,
    showFeedContextMenu,
    closeFeedContextMenu,
    setFeedOpenMethod,
    syncFeedFromContextMenu,
    markFeedAllAsRead,
    copyFeedLink,
    openFeedSiteInExternalBrowser,
    unsubscribeFeedFromContextMenu,
  }
}
