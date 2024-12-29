<template>
  <div class="latest-videos flex flex-col h-full">
    <SearchBar ref="searchBar" class="pt-4 px-4" @search="handleSearch"/>
    <div class="flex items-center justify-between py-1">
      <TabBar
          v-model="activeTab"
          :tabs="tabsWithCounts"
          class="custom-tab-bar flex-grow pl-4"
          @tab-dblclick="handleTabDoubleClick"
      />
      <SortButton
          v-model="sortBy"
          class="ml-2 pr-4"
          @update:modelValue="handleSortChange"
      />
    </div>

    <div class="video-container flex-grow">
      <router-view v-slot="{ Component }">
        <keep-alive :max="10">
          <component 
              :is="Component"
              :active-tab="activeTab"
              :search-query="searchQuery"
              :selected-subscription-id="subscriptionId"
              :sort-by="sortBy"
              @goToSubscription="goToChannelDetail"
              @openModal="handleOpenModal"
              @update-counts="updateCounts"
          />
        </keep-alive>
      </router-view>
    </div>
  </div>

  <div v-if="error" class="text-center py-4 text-red-500">
    {{ error }}
  </div>
</template>

<script setup>
import {computed, inject, onMounted, onUnmounted, ref, watch} from 'vue';
import {useRoute, useRouter} from 'vue-router';
import useLatestVideos from '../composables/useLatestVideos';
import SearchBar from '../components/SearchBar.vue';
import TabBar from '../components/TabBar.vue';
import SortButton from '../components/SortButton.vue';

const router = useRouter();
const emitter = inject('emitter');

const {
  videoContainer,
  error,
} = useLatestVideos();

const activeTab = ref('all');
const route = useRoute();
const subscriptionId = computed(() => route.params.id);

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
  },
  {
    value: 'preview',
    count: 0,
    label: '预告'
  },
  {
    value: 'liked',
    count: 0,
    label: '喜欢'
  }
]);

const searchQuery = ref('');

const sortBy = ref('uploaded_at');

const updateCounts = (counts) => {
  tabsWithCounts.value = counts;
};

const handleSearch = (keyword) => {
  searchQuery.value = keyword;
};

const handleOpenModal = (video, playlist) => {
  router.push(`/video/${video.video_id}`);
};

const goToChannelDetail = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`);
};

const handleSortChange = (newSort) => {
  sortBy.value = newSort;
};

const handleTabDoubleClick = (tab) => {
  if (tab === activeTab.value) {
    emitter.emit('reloadContent', activeTab.value);
  }
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

<style scoped src="../styles/components/LatestVideos.css"></style>

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

