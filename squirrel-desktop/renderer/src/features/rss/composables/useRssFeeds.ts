import { computed, onScopeDispose, ref, type Ref } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import { copyToClipboard } from '@/shared/lib/clipboard'
import { openExternalUrl } from '@/shared/lib/externalUrl'
import { usePointerOutside } from '@/shared/composables/usePointerOutside'
import { useContextMenuPosition } from '@/shared/composables/useContextMenuPosition'
import {
  getRssFeeds,
  markRssFeedAsRead,
  subscribeRssFeed,
  syncRssFeed,
  unsubscribeRssFeed,
  updateRssFeed,
} from '@/shared/api'
import type { RssEntry, RssFeed, RssFeedOpenMethod } from '@/features/rss/types/rss'

export function useRssFeeds(options: {
  selectedAccountId: Ref<number | null>
  canManageSubscriptions: Readonly<Ref<boolean>>
  onRefreshEntries?: (isReset?: boolean) => Promise<void>
  onStatus?: (message: string, isError?: boolean) => void
}) {
  const feeds = ref<RssFeed[]>([])
  const feedsError = ref('')
  const selectedFeedId = ref<number | null>(null)
  const loadingFeeds = ref(true)
  let feedsRequestToken = 0
  let subscribeSuccessTimer: ReturnType<typeof setTimeout> | null = null

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
  const { position: feedContextMenuPosition, positionMenu } = useContextMenuPosition()
  const contextMenuFeed = ref<RssFeed | null>(null)

  usePointerOutside(categoryDropdownRef, () => {
    showCategoryDropdown.value = false
  })

  const filteredFeeds = computed(() => {
    if (!options.selectedAccountId.value) return []
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
    const requestToken = ++feedsRequestToken
    const accountId = options.selectedAccountId.value
    loadingFeeds.value = true
    feedsError.value = ''

    if (!accountId) {
      feeds.value = []
      loadingFeeds.value = false
      return
    }

    try {
      const data = await getRssFeeds({ accountId })
      if (requestToken !== feedsRequestToken) return
      feeds.value = data?.data || []
    } catch (err) {
      if (requestToken !== feedsRequestToken) return
      feedsError.value = errorMessage(err, '加载订阅源失败')
      options?.onStatus?.(feedsError.value, true)
    } finally {
      if (requestToken === feedsRequestToken) {
        loadingFeeds.value = false
      }
    }
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
    if (subscribeSuccessTimer) {
      clearTimeout(subscribeSuccessTimer)
      subscribeSuccessTimer = null
    }
    showSubscribeModal.value = false
    showCategoryDropdown.value = false
    showCustomCategoryInput.value = false
    subscribeForm.value = { feedUrl: '', category: '', customCategory: '' }
    subscribeMessage.value = ''
    subscribeError.value = false
  }

  const handleSubscribeFeed = async () => {
    if (!options.canManageSubscriptions.value) {
      subscribeError.value = true
      subscribeMessage.value = '当前服务不支持添加订阅源'
      return
    }
    if (!options.selectedAccountId.value || !subscribeForm.value.feedUrl.trim()) return
    subscribingFeed.value = true
    subscribeMessage.value = ''
    subscribeError.value = false

    try {
      await subscribeRssFeed({
        accountId: options.selectedAccountId.value,
        feedUrl: subscribeForm.value.feedUrl.trim(),
        category: subscribeForm.value.category.trim() || undefined,
      })

      subscribeMessage.value = '订阅成功'
      subscribeSuccessTimer = setTimeout(() => {
        subscribeSuccessTimer = null
        closeSubscribeModal()
        void loadFeeds()
        void options?.onRefreshEntries?.(true)
      }, 1000)
    } catch (err) {
      subscribeError.value = true
      subscribeMessage.value = errorMessage(err, '订阅失败')
    } finally {
      subscribingFeed.value = false
    }
  }

  const toggleFolder = (name: string) => {
    collapsedFolders.value[name] = !collapsedFolders.value[name]
  }

  const selectFeed = async (feedId: number, refreshEntries = true) => {
    selectedFeedId.value = selectedFeedId.value === feedId ? null : feedId
    if (refreshEntries) await options?.onRefreshEntries?.(true)
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
    if (!options.canManageSubscriptions.value) {
      options?.onStatus?.('当前服务不支持取消订阅', true)
      return false
    }
    if (!options.selectedAccountId.value) return false
    try {
      await unsubscribeRssFeed(feed.id, options.selectedAccountId.value)
      if (selectedFeedId.value === feed.id) {
        selectedFeedId.value = null
      }
      options?.onStatus?.(`已取消订阅「${feed.title}」`)
      await loadFeeds()
      await options?.onRefreshEntries?.(true)
      return true
    } catch (err) {
      options?.onStatus?.(errorMessage(err, '取消订阅失败'), true)
      return false
    }
  }

  const showFeedContextMenu = (feed: RssFeed, event: MouseEvent) => {
    contextMenuFeed.value = feed
    positionMenu(event, feedContextMenuRef)
    showFeedContextMenuState.value = true
  }

  const closeFeedContextMenu = () => {
    showFeedContextMenuState.value = false
    contextMenuFeed.value = null
  }

  const setFeedOpenMethod = async (feed: RssFeed, method: RssFeedOpenMethod) => {
    try {
      await updateRssFeed(feed.id, { open_method: method })
      feed.open_method = method
      closeFeedContextMenu()
      options?.onStatus?.(
        method === 'external_browser'
          ? '已设为系统浏览器打开'
          : method === 'app_browser'
            ? '已设为应用内浏览器打开'
            : '已设为内嵌阅读'
      )
    } catch (err) {
      options?.onStatus?.(errorMessage(err, '更新失败'), true)
    }
  }

  const syncFeedFromContextMenu = async (feed: RssFeed) => {
    closeFeedContextMenu()
    try {
      const data = await syncRssFeed(feed.id)
      const count = (data as { entries?: number } | null)?.entries ?? 0
      options?.onStatus?.(`已同步「${feed.title}」，更新 ${count} 篇文章`)
      await options?.onRefreshEntries?.(true)
    } catch (err) {
      options?.onStatus?.(errorMessage(err, '同步失败'), true)
    }
  }

  const markFeedAllAsRead = async (feed: RssFeed) => {
    closeFeedContextMenu()
    try {
      await markRssFeedAsRead(feed.id)
      options?.onStatus?.(`已将「${feed.title}」全部文章标记为已读`)
      await options?.onRefreshEntries?.(true)
    } catch (err) {
      options?.onStatus?.(errorMessage(err, '标记失败'), true)
    }
  }

  const copyFeedLink = async (feed: RssFeed) => {
    closeFeedContextMenu()
    if (!feed.feed_url) {
      options?.onStatus?.('订阅源地址为空', true)
      return
    }
    const ok = await copyToClipboard(feed.feed_url)
    options?.onStatus?.(ok ? '已成功复制订阅源地址到剪贴板' : '复制链接失败', !ok)
  }

  const openFeedSiteInExternalBrowser = (feed: RssFeed) => {
    closeFeedContextMenu()
    if (feed.site_url) void openExternalUrl(feed.site_url)
  }

  onScopeDispose(() => {
    feedsRequestToken += 1
    if (subscribeSuccessTimer) clearTimeout(subscribeSuccessTimer)
  })

  return {
    feeds,
    feedsError,
    selectedFeedId,
    loadingFeeds,
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
  }
}
