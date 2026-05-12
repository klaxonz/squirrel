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
import { computed, ref, watch } from 'vue'
import VideoList from './VideoList.vue'
import useLatestVideos from '@/composables/useLatestVideos'

const emit = defineEmits(['openModal', 'goToSubscription', 'loading-change', 'error'])

const props = defineProps<{
  filters?: any
  searchQuery?: string
  activeTab?: string
  selectedSubscriptionId?: number
  sortBy?: string
  site?: string
  nsfw?: string
  timeRange?: string
  duration?: string
  contentType?: string
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
}))
const showChannelAvatar = computed(() => !currentFilters.value.subscription_id)

const {
  videos, loading, allLoaded, loadMore, handleSearch,
  searchQuery, activeTab, subscriptionId, sortBy, site, nsfw,
  timeRange, duration, contentType, error
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
  handleSearch()
}, { deep: true, immediate: true })

watch(error, (err) => err && emit('error', err))
watch(loading, (val) => emit('loading-change', val))

defineExpose({ refresh: () => handleSearch() })
</script>
