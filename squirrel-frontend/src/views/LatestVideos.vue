<template>
  <AppPageShell class="latest-videos-page" variant="compact" :fill="false">
    <!-- Channel Header -->
    <ChannelHeader v-if="subscriptionId" :subscription-id="subscriptionId" />

    <!-- Sticky Toolbar -->
    <div class="sticky top-0 z-30">
      <FeedToolbar
        :active-tab="activeTab"
        :nsfw="nsfw"
        :sort-by="sortBy"
        :site="site"
        :subscription-id="subscriptionId"
        :tabs="tabs"
        :is-refreshing="isRefreshing"
        :show-tabs="searchMode === 'local'"
        :show-sort="searchMode === 'local'"
        :show-filter="searchMode === 'local'"
        @update:activeTab="activeTab = $event"
        @update:nsfw="nsfw = $event"
        @update:sortBy="sortBy = $event"
        @update:site="site = $event"
        @refresh="refreshCurrentList"
      />
    </div>

    <!-- Main Content Area -->
    <div class="app-page-content">
      <div v-if="loadError" class="px-6 pt-6">
        <div class="bg-destructive/5 border border-destructive/20 rounded-2xl p-4 flex items-center justify-between">
          <p class="text-sm text-destructive font-medium">{{ loadError?.message || loadError }}</p>
          <button @click="refreshCurrentList" class="text-xs font-bold uppercase tracking-widest px-4 py-2 bg-destructive text-white rounded-full">重试</button>
        </div>
      </div>

      <RemoteSearchResults
        v-if="searchMode === 'remote'"
        ref="remoteSearchRef"
        :query="searchQuery"
        :site="site"
        @error="loadError = $event"
        @loading-change="isRefreshing = !!$event"
      />

      <router-view v-else v-slot="{ Component }">
        <keep-alive :max="10">
          <component
            :is="Component"
            :filters="childFilters"
            ref="videoChildRef"
            @goToSubscription="goToChannelDetail"
            @openModal="handleOpenModal"
            @error="loadError = $event"
            @loading-change="isRefreshing = !!$event"
          />
        </keep-alive>
      </router-view>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUIStore } from '@/stores/ui'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import ChannelHeader from '@/components/feed/ChannelHeader.vue'
import RemoteSearchResults from '@/components/feed/RemoteSearchResults.vue'
import AppPageShell from '@/components/layout/AppPageShell.vue'
import { VIDEO_TABS } from '@/constants/videos'
import { rememberVideoPlaybackSeed } from '@/composables/videoPlaybackSeed'
import { onSubscriptionRemoved } from '@/utils/subscriptionEvents'

defineOptions({ name: 'LatestVideos' })

const router = useRouter()
const route = useRoute()
const uiStore = useUIStore()

const subscriptionId = computed(() => route.params.id as string)
const { activeTab, nsfw, sortBy, site, searchQuery, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const loadError = ref<any>(null)
const videoChildRef = ref<any>(null)
const remoteSearchRef = ref<any>(null)
const searchMode = computed({
  get: () => uiStore.homeSearchMode,
  set: (value: 'local' | 'remote') => uiStore.setHomeSearchMode(value),
})

const childFilters = computed(() => filters.value)

const refreshCurrentList = () => {
  loadError.value = null
  if (searchMode.value === 'remote') {
    remoteSearchRef.value?.refresh?.()
    return
  }
  videoChildRef.value?.refresh?.()
}

const handleOpenModal = (video: any) => {
  rememberVideoPlaybackSeed(video)
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (id: string) => router.push(`/subscription/${id}/all`)

const handleTabDoubleClick = (tab: string) => {
  if (tab === activeTab.value) refreshCurrentList()
}

useRefreshTriggers({ onRefresh: refreshCurrentList })
useRouteTabSync(router, route, activeTab, subscriptionId)

watch(() => uiStore.searchTrigger, () => {
  if (route.meta.search === 'home' || !route.meta.search) {
    searchQuery.value = uiStore.searchQuery
  }
})

watch(subscriptionId, (value) => {
  if (value && searchMode.value === 'remote') {
    searchMode.value = 'local'
  }
})

watch(searchMode, (value) => {
  if (value === 'remote') {
    site.value = undefined
  }
})

onMounted(() => {
  onSubscriptionRemoved(({ subscriptionId }) => {
    if (String(route.params.id || '') === String(subscriptionId)) router.replace({ name: 'AllVideos' })
  })
})
</script>

<style scoped>
.latest-videos-page {
  --app-page-max-width: 2400px;
}
</style>
