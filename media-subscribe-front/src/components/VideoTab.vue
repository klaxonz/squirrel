<template>
  <keep-alive>
    <VideoList
        :key="`video-list-${$route.name}`"
        :videos="processedVideos"
        :loading="loading"
        :allLoaded="allLoaded"
        :showAvatar="false"
        @loadMore="loadMore"
        @toggleOptions="toggleOptions"
        @openModal="(video) => emit('openModal', video, videos)"
        @goToSubscription="(newSubscriptionId) => emit('goToSubscription', newSubscriptionId)"
    />
  </keep-alive>
</template>

<script setup>
import {computed, inject, onMounted} from 'vue';
import VideoList from "./VideoList.vue";
import useLatestVideos from "../composables/useLatestVideos.js";
import useVideoOperations from "../composables/useVideoOperations.js";
import useOptionsMenu from "../composables/useOptionsMenu.js";
import {defineEmits, watch} from "vue";


const emitter = inject('emitter');
const emit = defineEmits(['openModal', 'update-counts', 'goToSubscription']);

const props = defineProps({
  searchQuery: {
    type: String,
    default: ''
  },
  activeTab: String,
  selectedSubscriptionId: Number,
  sortBy: {
    type: String,
    default: 'uploaded_at'
  }
});

const {
  videos,
  loading,
  allLoaded,
  loadMore,
  searchQuery,
  handleSearch,
  activeTab,
  tabsWithCounts,
  subscriptionId,
  sortBy
} = useLatestVideos();

const processedVideos = computed(() => {
  return videos.value.map(video => ({
    ...video,
    showProgress: true,
    progress: video.last_position / video.total_duration
  }));
});

watch(() => props.activeTab, (newTab) => {
  activeTab.value = newTab;
  handleSearch();
})

watch(() => props.searchQuery, (newQuery) => {
  searchQuery.value = newQuery;
  handleSearch()
});

watch(() => tabsWithCounts.value, (newCounts) => {
  emit('update-counts', newCounts);
});

watch(() => props.selectedSubscriptionId, (newSubscriptionId) => {
  subscriptionId.value = newSubscriptionId;
  handleSearch();
})

watch(() => props.sortBy, () => {
  sortBy.value = props.sortBy;
  handleSearch();
});
const {
  toggleOptions,
} = useOptionsMenu(videos);

onMounted(async () => {
  subscriptionId.value = props.selectedSubscriptionId;
  emitter.on('reloadContent', (tab) => {
    handleSearch();
  });
  await loadMore();


})

</script>

<style scoped>

</style>