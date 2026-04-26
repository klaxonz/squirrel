import { computed, ref } from 'vue'
import type { Ref } from 'vue'

export type TimeRange = 'all' | 'today' | 'week' | 'month' | 'year'
export type Duration = 'all' | 'short' | 'medium' | 'long'
export type ContentType = 'all' | 'CHANNEL' | 'PLAYLIST' | 'ACTRESS' | 'MOVIE' | 'TV_SERIES' | 'ACTOR'

type SubscriptionId = string | number | null | undefined

export function useFeedFilters({ subscriptionIdRef }: { subscriptionIdRef?: Ref<SubscriptionId> } = {}) {
  const activeTab = ref('all')
  const nsfw = ref('all')
  const sortBy = ref('publish_date')
  const site = ref<string | undefined>(undefined)
  const searchQuery = ref('')
  const timeRange = ref<TimeRange>('all')
  const duration = ref<Duration>('all')
  const contentType = ref<ContentType>('all')

  const filters = computed(() => ({
    tab: activeTab.value,
    q: searchQuery.value,
    subscription_id: subscriptionIdRef?.value,
    sort_by: sortBy.value,
    nsfw: nsfw.value === 'only' ? 'yes' : nsfw.value,
    site: subscriptionIdRef?.value ? undefined : site.value,
    timeRange: timeRange.value,
    duration: duration.value,
    contentType: contentType.value,
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
    filters,
  }
}


