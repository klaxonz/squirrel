import { computed, ref } from 'vue';

export function useFeedFilters({ subscriptionIdRef } = {}) {
  const activeTab = ref('all');
  const nsfw = ref('all');
  const sortBy = ref('publish_date');
  const site = ref();
  const searchQuery = ref('');

  const filters = computed(() => ({
    tab: activeTab.value,
    q: searchQuery.value,
    sid: subscriptionIdRef?.value,
    sort: sortBy.value,
    nsfw: nsfw.value,
    site: subscriptionIdRef?.value ? undefined : site.value,
  }));

  return {
    activeTab,
    nsfw,
    sortBy,
    site,
    searchQuery,
    filters,
  };
}


