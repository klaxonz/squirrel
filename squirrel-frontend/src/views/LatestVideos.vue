<template>
  <div class="latest-videos flex flex-col h-full">
    <ChannelHeader
      v-if="subscriptionId"
      :subscription-id="subscriptionId"
    />
    <!-- 顶部操作栏 - TabBar 和 SortButton -->
    <div class="toolbar-container">
      <FeedToolbar
        :active-tab="activeTab"
        :nsfw="nsfw"
        :sort-by="sortBy"
        :site="site"
        :subscription-id="subscriptionId"
        :tabs-with-counts="tabsWithCounts"
        :is-refreshing="isRefreshing"
        @update:activeTab="(v) => activeTab = v"
        @update:nsfw="(v) => nsfw = v"
        @update:sortBy="(v) => sortBy = v"
        @update:site="(v) => site = v"
        @tab-dblclick="handleTabDoubleClick"
        @refresh="refreshCurrentList"
      />
    </div>

    <div class="video-container flex-grow">
      <div v-if="loadError" class="alert-container">
        <InlineAlert
          :message="`加载失败：${loadError?.message || loadError}`"
          action-label="重试"
          @action="refreshCurrentList"
        />
      </div>
      <router-view v-slot="{ Component }">
        <keep-alive :max="10">
          <component
              :is="Component"
              :filters="childFilters"
              ref="videoChildRef"
              @goToSubscription="goToChannelDetail"
              @openModal="handleOpenModal"
              @update-counts="updateCounts"
              @error="(e) => (loadError = e)"
              @loading-change="(val) => (isRefreshing = !!val)"
          />
        </keep-alive>
      </router-view>
    </div>
  </div>

  
</template>

<script setup>
import { computed, inject, onActivated, onDeactivated, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '../components/feed/FeedToolbar.vue'
import ChannelHeader from '../components/ChannelHeader.vue'
import { InlineAlert } from '@/components/common'
import { buildTabsWithCounts } from '../utils/feed'

const router = useRouter();
const emitter = inject('emitter');

// Page-scoped filter state
const route = useRoute();
const subscriptionId = computed(() => route.params.id);
const { activeTab, nsfw, sortBy, site, searchQuery, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId });
const childFilters = computed(() => filters.value);

const tabsWithCounts = ref(buildTabsWithCounts({}));

const isRefreshing = ref(false);
const loadError = ref(null);

const videoChildRef = ref(null);

const refreshCurrentList = () => {
  isRefreshing.value = true;
  loadError.value = null;
  videoChildRef.value?.refresh?.();
};

useRefreshTriggers({ onRefresh: () => refreshCurrentList() });


const updateCounts = (counts) => {
  tabsWithCounts.value = buildTabsWithCounts(counts);
};

// 处理全局搜索事件
const handleGlobalSearch = (keyword) => {
  searchQuery.value = keyword;
};

const handleOpenModal = (video) => {
  // 从列表页进入时，直接跳转，不传递复杂对象
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (subscriptionId) => {
  router.push(`/subscription/${subscriptionId}/all`)
}


const handleTabDoubleClick = (tab) => {
  if (tab === activeTab.value) {
    isRefreshing.value = true;
    videoChildRef.value?.refresh?.();
  }
};

useRouteTabSync(router, route, activeTab, subscriptionId);

onActivated(() => {
  emitter.on('search:home', handleGlobalSearch);
});

onDeactivated(() => {
  emitter.off('search:home', handleGlobalSearch);
});

// Tab-route sync moved to composable

</script>

<style scoped src="../styles/components/LatestVideos.css"></style>

<style scoped>
.latest-videos {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.video-container {
  flex: 1;
  overflow: hidden;
}

.toolbar-container,
.alert-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding: 0 1rem;
  width: 100%;
}

@media (min-width: 640px) {
  .toolbar-container,
  .alert-container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .alert-container {
    padding: 0 2rem;
  }
}

@keyframes spin { to { transform: rotate(360deg); } }
.spin-anim { animation: spin 0.8s linear infinite; }
</style>

