<template>
  <keep-alive>
    <VideoList
        :key="`video-list-${$route.name}`"
        :videos="processedVideos"
        :loading="loading"
        :allLoaded="allLoaded"
        :showAvatar="false"
        :sortBy="sortBy"
        :refreshing="isResetting"
        @loadMore="loadMore"
        @toggleOptions="toggleOptions"
        @openModal="(video) => emit('openModal', video, videos)"
        @goToSubscription="(newSubscriptionId) => emit('goToSubscription', newSubscriptionId)"
    />
  </keep-alive>
</template>

<script setup>
import { computed, watch } from 'vue'
import VideoList from './VideoList.vue'
import useLatestVideos from '@/composables/useLatestVideos.js'
import useOptionsMenu from '@/composables/useOptionsMenu.js'

const emit = defineEmits(['openModal', 'update-counts', 'goToSubscription', 'loading-change']);

const props = defineProps({
  // New unified filters prop (preferred)
  filters: {
    type: Object,
    default: null,
  },
  // Back-compat individual props (will be derived if filters missing)
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
})

// 辅助函数：统一处理props映射
const getFiltersFromProps = () => ({
  tab: props.filters?.tab ?? props.activeTab ?? 'all',
  q: props.filters?.q ?? props.searchQuery ?? '',
  sid: props.filters?.sid ?? props.selectedSubscriptionId ?? null,
  sort: props.filters?.sort ?? props.sortBy ?? 'publish_date',
  site: props.filters?.site ?? props.site,
  nsfw: props.filters?.nsfw ?? props.nsfw ?? 'all',
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
  isResetting,
  site,
  nsfw,
  videoCounts,
  error,
} = useLatestVideos({
  activeTab: getFiltersFromProps().tab,
  searchQuery: getFiltersFromProps().q,
  subscriptionId: getFiltersFromProps().sid,
  sortBy: getFiltersFromProps().sort,
  site: getFiltersFromProps().site,
  nsfw: getFiltersFromProps().nsfw,
})

const processedVideos = computed(() => {
  return videos.value.map(video => ({
    ...video,
    showProgress: true,
    progress: video.duration > 0 ? (video.last_position / video.duration) : 0
  }));
});

watch(() => videoCounts.value, (counts) => {
  emit('update-counts', counts);
}, { immediate: true });

watch(() => error.value, (err) => {
  emit('error', err);
});

watch(
  getFiltersFromProps,
  (filters) => {
    activeTab.value = filters.tab
    searchQuery.value = filters.q
    subscriptionId.value = filters.sid
    sortBy.value = filters.sort
    site.value = filters.site
    nsfw.value = filters.nsfw
    handleSearch()
  },
  { immediate: true }
)
const {
  toggleOptions,
} = useOptionsMenu(videos);

watch(() => loading.value, (val) => {
  emit('loading-change', val);
});

defineExpose({
  refresh: () => handleSearch(),
});

</script>

<style scoped>

</style>
