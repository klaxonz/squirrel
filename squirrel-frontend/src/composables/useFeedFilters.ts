import { computed, ref } from 'vue'
import type { Ref } from 'vue'

type SubscriptionId = string | number | null | undefined

export function useFeedFilters({ subscriptionIdRef }: { subscriptionIdRef?: Ref<SubscriptionId> } = {}) {
  const activeTab = ref('all')
  const nsfw = ref('all')
  const sortBy = ref('publish_date')
  const site = ref<string | undefined>(undefined)
  const searchQuery = ref('')

  const filters = computed(() => ({
    tab: activeTab.value,
    q: searchQuery.value,
    sid: subscriptionIdRef?.value,
    sort: sortBy.value,
    nsfw: nsfw.value,
    site: subscriptionIdRef?.value ? undefined : site.value,
  }))

  return {
    activeTab,
    nsfw,
    sortBy,
    site,
    searchQuery,
    filters,
  }
}


