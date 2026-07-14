import { computed, type ComputedRef, type Ref } from 'vue'
import type { RssAccount, RssEntry, RssFeed } from './rssTypes'

/**
 * Header display derivation for the RSS sources view.
 *
 * Computes the title + subtitle shown above the entry list based on the current
 * filter context: "recent" view, a specific selected feed, or the whole account.
 * Pure presentation logic that previously sat between the composable wiring and
 * the lifecycle block in RssSources.vue; extracted so the view's script reads as
 * "wire composables → derive header → orchestrate" without interleaved formulae.
 */
export interface UseRssFeedHeaderOptions {
  activeFilter: ComputedRef<string> | Ref<string>
  selectedFeedId: ComputedRef<number | null> | Ref<number | null>
  feeds: ComputedRef<RssFeed[]> | Ref<RssFeed[]>
  recentlyViewed: ComputedRef<RssEntry[]> | Ref<RssEntry[]>
  totalEntries: ComputedRef<number> | Ref<number>
  selectedAccount: ComputedRef<RssAccount | null> | Ref<RssAccount | null>
}

export interface UseRssFeedHeaderReturn {
  selectedFeedTitle: ComputedRef<string | null>
  selectedFeedSubtitle: ComputedRef<string>
}

const RECENT_TITLE = '最近浏览'
const UNTITLED_FEED = '订阅源'
const UNCATEGORIZED = '未分类'
const ACCOUNT_FALLBACK = '浏览您的 RSS 服务内容源'

export function useRssFeedHeader(options: UseRssFeedHeaderOptions): UseRssFeedHeaderReturn {
  const { activeFilter, selectedFeedId, feeds, recentlyViewed, totalEntries, selectedAccount } = options

  const selectedFeedTitle = computed<string | null>(() => {
    if (activeFilter.value === 'recent') return RECENT_TITLE
    if (selectedFeedId.value) {
      return feeds.value.find((f) => f.id === selectedFeedId.value)?.title || UNTITLED_FEED
    }
    return null
  })

  const selectedFeedSubtitle = computed<string>(() => {
    if (activeFilter.value === 'recent') {
      return `共 ${recentlyViewed.value.length} 篇最近浏览的文章`
    }
    if (selectedFeedId.value) {
      const feed = feeds.value.find((f) => f.id === selectedFeedId.value)
      return `${feed?.category || UNCATEGORIZED} · ${totalEntries.value} 篇文章`
    }
    if (selectedAccount.value) {
      return `共 ${totalEntries.value} 篇文章`
    }
    return ACCOUNT_FALLBACK
  })

  return {
    selectedFeedTitle,
    selectedFeedSubtitle,
  }
}
