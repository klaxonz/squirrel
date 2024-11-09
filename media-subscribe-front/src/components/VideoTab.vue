<template>
  <VideoList
      :videos="videos"
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
      @goToChannel="(channelId) => emit('goToChannel', channelId)"
  />

</template>


<script setup>
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
  selectedChannelId: String
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
  channelId
} = useLatestVideos();

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
  console.log('watch selectedChannelId', newChannelId);
  channelId.value = newChannelId;
  handleSearch();
})

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
  console.log('onMounted');
  await loadMore();
})

</script>

<style scoped>

</style>