<template>
  <VideoList
    :videos="videos"
    :loading="loading"
    :allLoaded="allLoaded"
    :showAvatar="showChannelAvatar"
    :sortBy="sortBy"
    :refreshing="loading && videos.length > 0"
    @loadMore="loadMore"
    @openModal="(video) => emit('openModal', video, videos)"
    @goToSubscription="(id) => emit('goToSubscription', id)"
  />
</template>

<script setup lang="ts">
import { computed, watch } from 'vue'
import VideoList from './VideoList.vue'
import useLatestVideos from '@/composables/useLatestVideos'
import type { FeedFilters } from '@/composables/useFeedFilters'

const emit = defineEmits(['openModal', 'goToSubscription', 'loading-change', 'error', 'loaded'])

const props = defineProps<{
  filters?: FeedFilters
  searchQuery?: string
  activeTab?: string
  selectedSubscriptionId?: number
  sortBy?: string
  site?: string
  nsfw?: string
  timeRange?: string
  duration?: string
  contentType?: string
  special?: string
}>()

const currentFilters = computed(() => ({
  tab: props.filters?.tab ?? props.activeTab ?? 'all',
  q: props.filters?.q ?? props.searchQuery ?? '',
  subscription_id: props.filters?.subscription_id ?? props.selectedSubscriptionId ?? null,
  sort: props.filters?.sort_by ?? props.sortBy ?? 'publish_date',
  site: props.filters?.site ?? props.site,
  nsfw: props.filters?.nsfw ?? props.nsfw ?? 'all',
  timeRange: props.filters?.timeRange ?? 'all',
  duration: props.filters?.duration ?? 'all',
  contentType: props.filters?.contentType ?? 'all',
  special: props.filters?.special ?? 'all',
}))
const showChannelAvatar = computed(() => !currentFilters.value.subscription_id)

const {
  videos, loading, allLoaded, loadMore, handleSearch,
  searchQuery, activeTab, subscriptionId, sortBy, site, nsfw,
  timeRange, duration, contentType, special, error
} = useLatestVideos({
  activeTab: currentFilters.value.tab,
  searchQuery: currentFilters.value.q,
  subscriptionId: currentFilters.value.subscription_id,
  sortBy: currentFilters.value.sort,
  site: currentFilters.value.site,
  nsfw: currentFilters.value.nsfw,
  timeRange: currentFilters.value.timeRange,
  duration: currentFilters.value.duration,
  contentType: currentFilters.value.contentType,
  special: currentFilters.value.special,
})

watch(currentFilters, (f) => {
  activeTab.value = f.tab
  searchQuery.value = f.q
  subscriptionId.value = f.subscription_id
  sortBy.value = f.sort
  site.value = f.site
  nsfw.value = f.nsfw
  timeRange.value = f.timeRange
  duration.value = f.duration
  contentType.value = f.contentType
  special.value = f.special
  handleSearch()
}, { deep: true, immediate: true })

watch(error, (err) => err && emit('error', err))
watch(loading, (val) => emit('loading-change', val))
watch(videos, (val) => emit('loaded', val), { deep: true, immediate: true })

defineExpose({ refresh: () => handleSearch() })
</script>
