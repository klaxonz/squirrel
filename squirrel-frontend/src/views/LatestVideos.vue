<template>
  <div class="latest-videos flex h-full flex-col">
    <ChannelHeader
      v-if="subscriptionId"
      :subscription-id="subscriptionId"
    />

    <section v-else class="latest-videos__toolbar-shell">
      <div class="latest-videos__container">
        <PageHeader
          title="最新内容"
          description="统一查看最新视频、未读内容和稍后处理队列。"
        />
      </div>
    </section>

    <section class="latest-videos__toolbar-shell">
      <div class="latest-videos__container">
        <FeedToolbar
          :active-tab="activeTab"
          :nsfw="nsfw"
          :sort-by="sortBy"
          :site="site"
          :subscription-id="subscriptionId"
          :tabs-with-counts="tabsWithCounts"
          :is-refreshing="isRefreshing"
          @update:activeTab="(value) => activeTab = value"
          @update:nsfw="(value) => nsfw = value"
          @update:sortBy="(value) => sortBy = value"
          @update:site="(value) => site = value"
          @tab-dblclick="handleTabDoubleClick"
          @refresh="refreshCurrentList"
        />
      </div>
    </section>

    <div class="video-container flex-grow">
      <div v-if="loadError" class="latest-videos__container latest-videos__alert">
        <Alert variant="destructive" class="flex items-start justify-between gap-3">
          <div class="min-w-0">
            <AlertTitle>加载失败</AlertTitle>
            <AlertDescription class="break-words">
              {{ `加载失败：${loadError?.message || loadError}` }}
            </AlertDescription>
          </div>
          <Button variant="secondary" size="sm" class="rounded-full" @click="refreshCurrentList">重试</Button>
        </Alert>
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
            @error="(error) => (loadError = error)"
            @loading-change="(value) => (isRefreshing = !!value)"
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
import FeedToolbar from '@/components/feed/FeedToolbar.vue'
import ChannelHeader from '@/components/feed/ChannelHeader.vue'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import PageHeader from '@/components/layout/PageHeader.vue'
import { buildTabsWithCounts } from '../utils/feed'

const router = useRouter()
const route = useRoute()
const emitter = inject('emitter')

const subscriptionId = computed(() => route.params.id)
const { activeTab, nsfw, sortBy, site, searchQuery, filters } = useFeedFilters({ subscriptionIdRef: subscriptionId })

const tabsWithCounts = ref(buildTabsWithCounts({}))
const isRefreshing = ref(false)
const loadError = ref(null)
const videoChildRef = ref(null)

const childFilters = computed(() => filters.value)

const refreshCurrentList = () => {
  isRefreshing.value = true
  loadError.value = null
  videoChildRef.value?.refresh?.()
}

const updateCounts = (counts) => {
  tabsWithCounts.value = buildTabsWithCounts(counts)
}

const handleGlobalSearch = (keyword) => {
  searchQuery.value = keyword
}

const handleOpenModal = (video) => {
  router.push(`/video/${video.id}`)
}

const goToChannelDetail = (targetSubscriptionId) => {
  router.push(`/subscription/${targetSubscriptionId}/all`)
}

const handleTabDoubleClick = (tab) => {
  if (tab === activeTab.value) {
    isRefreshing.value = true
    videoChildRef.value?.refresh?.()
  }
}

useRefreshTriggers({ onRefresh: refreshCurrentList })
useRouteTabSync(router, route, activeTab, subscriptionId)

onActivated(() => {
  emitter?.on?.('search:home', handleGlobalSearch)
})

onDeactivated(() => {
  emitter?.off?.('search:home', handleGlobalSearch)
})
</script>

<style scoped src="../styles/components/LatestVideos.css"></style>
