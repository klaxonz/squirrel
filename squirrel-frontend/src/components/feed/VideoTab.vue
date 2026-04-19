<template>
  <VideoList
      :videos="videos"
      :loading="loading"
      :allLoaded="allLoaded"
      :showAvatar="false"
      :sortBy="sortBy"
      :scroll-cache-key="listScrollCacheKey"
      @loadMore="loadMore"
      @openModal="(video) => emit('openModal', video, videos)"
      @goToSubscription="(newSubscriptionId) => emit('goToSubscription', newSubscriptionId)"
  />
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import VideoList from './VideoList.vue'
import useLatestVideos from '@/composables/useLatestVideos'

const emit = defineEmits(['openModal', 'goToSubscription', 'loading-change', 'error']);

const props = defineProps({
  filters: {
    type: Object,
    default: null,
  },
  searchQuery: {
    type: String,
    default: '',
  },
  activeTab: {
    type: String,
    default: 'all',
  },
  selectedSubscriptionId: {
    type: Number,
    default: null,
  },
  sortBy: {
    type: String,
    default: 'publish_date',
  },
  site: {
    type: String,
    default: undefined,
  },
  nsfw: {
    type: String,
    default: 'all',
  },
  timeRange: {
    type: String,
    default: 'all',
  },
  duration: {
    type: String,
    default: 'all',
  },
  contentType: {
    type: String,
    default: 'all',
  },
})

const getFiltersFromProps = () => ({
  tab: props.filters?.tab ?? props.activeTab ?? 'all',
  q: props.filters?.q ?? props.searchQuery ?? '',
  sid: props.filters?.sid ?? props.selectedSubscriptionId ?? null,
  sort: props.filters?.sort ?? props.sortBy ?? 'publish_date',
  site: props.filters?.site ?? props.site,
  nsfw: props.filters?.nsfw ?? props.nsfw ?? 'all',
  timeRange: props.filters?.timeRange ?? 'all',
  duration: props.filters?.duration ?? 'all',
  contentType: props.filters?.contentType ?? 'all',
})

const {
  videos,
  loading,
  allLoaded,
  loadMore,
  searchQuery,
  handleSearch,
  activeTab,
  subscriptionId,
  sortBy,
  site,
  nsfw,
  timeRange,
  duration,
  contentType,
  error,
} = useLatestVideos({
  activeTab: getFiltersFromProps().tab,
  searchQuery: getFiltersFromProps().q,
  subscriptionId: getFiltersFromProps().sid,
  sortBy: getFiltersFromProps().sort,
  site: getFiltersFromProps().site,
  nsfw: getFiltersFromProps().nsfw,
  timeRange: getFiltersFromProps().timeRange,
  duration: getFiltersFromProps().duration,
  contentType: getFiltersFromProps().contentType,
})

const lastSignature = ref('')
const listScrollCacheKey = computed(() => {
  const filters = getFiltersFromProps()
  return [
    filters.sid ?? 'all',
    filters.tab,
    filters.q,
    filters.sort,
    filters.site ?? '',
    filters.nsfw,
    filters.timeRange,
    filters.duration,
    filters.contentType,
  ].join('\x00')
})

const applyFilters = (filters) => {
  const nextSignature = [
    filters.tab,
    filters.q,
    filters.sid,
    filters.sort,
    filters.site,
    filters.nsfw,
    filters.timeRange,
    filters.duration,
    filters.contentType,
  ].join('\x00')

  if (lastSignature.value && nextSignature === lastSignature.value) return

  activeTab.value = filters.tab
  searchQuery.value = filters.q
  subscriptionId.value = filters.sid
  sortBy.value = filters.sort
  site.value = filters.site
  nsfw.value = filters.nsfw
  timeRange.value = filters.timeRange
  duration.value = filters.duration
  contentType.value = filters.contentType
  lastSignature.value = nextSignature

  handleSearch()
}

watch(
  getFiltersFromProps,
  (filters) => applyFilters(filters),
  { immediate: true }
)

watch(error, (err) => {
  if (err !== undefined) emit('error', err)
})

watch(loading, (val) => {
  emit('loading-change', val)
})

defineExpose({
  refresh: () => handleSearch(),
})
</script>

<style scoped>

</style>
