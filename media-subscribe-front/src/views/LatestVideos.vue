<template>
  <div class="latest-videos flex flex-col h-full mx-4">
    <SearchBar class="pt-4" @search="handleSearch" ref="searchBar" />
    <TabBar v-model="activeTab" :tabs="tabsWithCounts" class="custom-tab-bar" />

    <div class="video-container pt-1 flex-grow">
      <router-view 
        v-slot="{ Component }" 
      >
        <component
          :is="Component"
          :active-tab="activeTab"
          :search-query="searchQuery"
          :selected-channel-id="channelId"
          @update-counts="updateCounts"
          @openModal="handleOpenModal"
          @goToChannel="goToChannelDetail"
        />
      </router-view>
    </div>
  </div>

  <div v-if="error" class="text-center py-4 text-red-500">
    {{ error }}
  </div>
</template>

<script setup>
import {onMounted, inject, ref, computed, watch, onUnmounted} from 'vue';
import { useRoute, useRouter } from 'vue-router';
import useLatestVideos from '../composables/useLatestVideos';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';

const router = useRouter();
const emitter = inject('emitter');

const {
  videoContainer,
  videos,
  error,
} = useLatestVideos();

const activeTab = ref('all');
const route = useRoute();
const channelId = computed(() => route.params.id);

const tabsWithCounts = ref([
  {
    value: 'all',
    count: 0,
    label: '全部'
  },
  {
    value: 'unread',
    count: 0,
    label: '未读'
  },
  {
    value: 'read',
    count: 0,
    label: '已读'
  }
]);

const searchQuery = ref('');

const updateCounts = (counts) => {
  tabsWithCounts.value = counts;
};

const handleSearch = (keyword) => {
  searchQuery.value = keyword;
};

const handleOpenModal = (video, playlist) => {
  emitter.emit('openVideoModal', { video, playlist });
};

const goToChannelDetail = (newChannelId) => {
  router.push(`/channel/${newChannelId}/all`);
};

watch(() => activeTab.value, (newVal) => {
  router.push(`/videos/${newVal}`);
});

onMounted(() => {
  emitter.on('sidebarStateChanged', () => {
    if (videoContainer.value) {
      videoContainer.value.dispatchEvent(new Event('resize'));
    }
  });
});

onUnmounted(() => {
  emitter.off('sidebarStateChanged');
});
</script>

<style src="./LatestVideos.css" scoped></style>

<style scoped>
.latest-videos {
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.video-container {
  flex: 1;
  overflow: hidden;
}
</style>

