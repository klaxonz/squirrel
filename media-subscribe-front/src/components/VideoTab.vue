<template>
  <VideoList
      :videos="processedVideos"
      :loading="loading"
      :allLoaded="allLoaded"
      :showAvatar="false"
      :is-channel-page="true"
      @loadMore="loadMore"
      @play="playVideo"
      @videoPlay="onVideoPlay"
      @videoPause="onVideoPause"
      @videoEnded="onVideoEnded"
      @toggleOptions="toggleOptions"
      @openModal="(video) => emit('openModal', video, videos)"
      @goToChannel="(newChannelId) => emit('goToChannel', newChannelId)"
  />

</template>


<script setup>
import { computed } from 'vue';
import VideoList from "./VideoList.vue";
import useLatestVideos from "../composables/useLatestVideos.js";
import useVideoOperations from "../composables/useVideoOperations.js";
import useOptionsMenu from "../composables/useOptionsMenu.js";
import {defineEmits, onActivated, onDeactivated, onMounted, watch} from "vue";

const emit = defineEmits(['openModal', 'update-counts', 'goToChannel']);

const props = defineProps({
  searchQuery: {
    type: String,
    default: ''
  },
  activeTab: String,
  selectedChannelId: String,
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
  channelId,
  sortBy
} = useLatestVideos();

// 添加计算属性来处理视频进度
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

watch(() => props.selectedChannelId, (newChannelId) => {
  channelId.value = newChannelId;
  handleSearch();
})

watch(() => props.sortBy, () => {
  sortBy.value = props.sortBy;
  handleSearch();
});

const {
  playVideo,
  onVideoPlay,
  onVideoPause,
  onVideoEnded,
} = useVideoOperations(videos);

const {
  toggleOptions,
} = useOptionsMenu(videos);

onMounted(async () => {
  channelId.value = props.selectedChannelId;
  await loadMore();
})

</script>

<style scoped>

</style>