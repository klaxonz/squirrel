<template>
  <div class="latest-videos flex flex-col h-full">
    <!-- 顶部操作栏 - TabBar 和 SortButton -->
    <div class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between py-3">
      <TabBar
          v-model="activeTab"
          :tabs="tabsWithCounts"
          class="custom-tab-bar flex-grow"
          @tab-dblclick="handleTabDoubleClick"
      />
        <div class="flex items-center">
          <NsfwFilter v-model="nsfw" class="ml-2" @update:modelValue="handleNsfwChange" />
          <SortButton
              v-model="sortBy"
              class="ml-2"
              @update:modelValue="handleSortChange"
          />
          <RefreshButton
            class="ml-2"
            :loading="isRefreshing"
            title="刷新 (R)"
            aria-label="刷新"
            @click="refreshCurrentList"
          />
        </div>
      </div>
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
              @loading-change="(val) => (isRefreshing = !!val)"
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
import TabBar from '../components/TabBar.vue';
import SortButton from '../components/SortButton.vue';
import NsfwFilter from '../components/NsfwFilter.vue';
import RefreshButton from '../components/RefreshButton.vue';

const router = useRouter();
const emitter = inject('emitter');

const {
  videoContainer,
  activeTab,
  error,
  nsfw,
  handleSearch
} = useLatestVideos();

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

const isRefreshing = ref(false);


const lastRefreshedAt = ref(Date.now());
const VISIBILITY_REFRESH_THRESHOLD_MS = 5 * 60 * 1000;

const refreshCurrentList = () => {
  isRefreshing.value = true;
  emitter.emit('reloadContent', activeTab.value);
  lastRefreshedAt.value = Date.now();
};

const handleKeyDown = (e) => {
  const target = e.target;
  if (target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)) return;
  if (e.ctrlKey || e.metaKey || e.altKey) return;
  if ((e.key === 'r' || e.key === 'R') && !e.repeat) {
    e.preventDefault();
    refreshCurrentList();
  }
};

const handleVisibilityChange = () => {
  if (!document.hidden) {
    if (Date.now() - lastRefreshedAt.value > VISIBILITY_REFRESH_THRESHOLD_MS) {
      refreshCurrentList();
    }
  }
};


const searchQuery = ref('');

const sortBy = ref('publish_date');

const updateCounts = (counts) => {
  tabsWithCounts.value = counts;
};

// 处理全局搜索事件
const handleGlobalSearch = (keyword) => {
  searchQuery.value = keyword;
};

const handleOpenModal = (video) => {
  router.push(`/video/${video.id}`);
};




const goToChannelDetail = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`);
};

const handleSortChange = (newSort) => {
  sortBy.value = newSort;
};

const handleNsfwChange = () => {
  handleSearch();
};


const handleTabDoubleClick = (tab) => {
  if (tab === activeTab.value) {
    isRefreshing.value = true;
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

  // 监听全局搜索事件
  emitter.on('search:home', handleGlobalSearch);


  // 键盘快捷键：R 刷新当前列表
  window.addEventListener('keydown', handleKeyDown);
  // 页面可见性变化：切回且超过阈值时自动刷新
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

onUnmounted(() => {
  emitter.off('reloadContent');

  emitter.off('sidebarStateChanged');
  emitter.off('search:home', handleGlobalSearch);
  window.removeEventListener('keydown', handleKeyDown);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});
  emitter.off('reloadContent');

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

@keyframes spin { to { transform: rotate(360deg); } }
.spin-anim { animation: spin 0.8s linear infinite; }
</style>

