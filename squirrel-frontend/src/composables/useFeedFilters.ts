import { computed, ref } from 'vue'
import type { Ref } from 'vue'

export type TimeRange = 'all' | 'today' | 'week' | 'month' | 'year'
export type Duration = 'all' | 'short' | 'medium' | 'long'
export type ContentType = 'all' | 'CHANNEL' | 'PLAYLIST' | 'ACTRESS' | 'MOVIE' | 'TV_SERIES' | 'ACTOR'
export type SpecialFollowFilter = 'all' | 'yes'

type SubscriptionId = string | number | null | undefined

// ponytail: shape mirrors the computed filters bag returned below; exported so
// consumers (VideoTab props) can type the inbound filter object.
export type FeedFilters = {
  tab?: string
  q?: string
  subscription_id?: SubscriptionId
  sort_by?: string
  nsfw?: string
  site?: string
  timeRange?: string
  duration?: string
  contentType?: string
  special?: string
}

export function useFeedFilters({ subscriptionIdRef }: { subscriptionIdRef?: Ref<SubscriptionId> } = {}) {
  const activeTab = ref('all')
  const nsfw = ref('all')
  const sortBy = ref('publish_date')
  const site = ref<string | undefined>(undefined)
  const searchQuery = ref('')
  const timeRange = ref<TimeRange>('all')
  const duration = ref<Duration>('all')
  const contentType = ref<ContentType>('all')
  const special = ref<SpecialFollowFilter>('all')

  const filters = computed<FeedFilters>(() => ({
    tab: activeTab.value,
    q: searchQuery.value,
    subscription_id: subscriptionIdRef?.value,
    sort_by: sortBy.value,
    nsfw: nsfw.value === 'only' ? 'yes' : nsfw.value,
    site: subscriptionIdRef?.value ? undefined : site.value,
    timeRange: timeRange.value,
    duration: duration.value,
    contentType: contentType.value,
    special: special.value,
  }))

  return {
    activeTab,
    nsfw,
    sortBy,
    site,
    searchQuery,
    timeRange,
    duration,
    contentType,
    special,
    filters,
  }
}

