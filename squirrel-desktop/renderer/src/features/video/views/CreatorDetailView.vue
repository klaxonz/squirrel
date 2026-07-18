<template>
  <AppPageShell class="creator-detail-page" variant="compact" surface="consume" width="media">
    <CreatorHeader
      :creator-id="creatorId"
      @loaded="creatorDetail = $event"
      @error="loadError = $event"
    />

    <AppToolbarFrame sticky bordered variant="compact">
      <FeedToolbar
        :active-tab="activeTab"
        :nsfw="nsfw"
        :sort-by="sortBy"
        :special="special"
        :time-range="timeRange"
        :duration="duration"
        :content-type="contentType"
        :tabs="tabs"
        :is-refreshing="isRefreshing"
        variant="workbench"
        :preference-key="`creator:${creatorId}`"
        :show-tabs="true"
        :show-sort="true"
        :show-filter="true"
        @update:activeTab="activeTab = $event"
        @update:nsfw="nsfw = $event"
        @update:sortBy="sortBy = $event"
        @update:timeRange="timeRange = $event"
        @update:duration="duration = $event"
        @update:content-type="contentType = $event"
        @update:special="setSpecialFilter"
        @refresh="refreshCurrentList"
      />
    </AppToolbarFrame>

    <div class="app-page-content app-page-content--media">
      <div v-if="loadError">
        <AppEmptyState variant="error" title="加载失败" :copy="loadError">
          <template #actions>
            <Button severity="secondary" outlined size="sm" @click="refreshCurrentList">重试</Button>
          </template>
        </AppEmptyState>
      </div>

      <router-view v-else v-slot="{ Component, route: childRoute }">
        <keep-alive :max="10">
          <component
            :is="Component"
            :key="childRoute.name"
            :filters="childFilters"
            presentation="workbench"
            interaction="open"
            ref="videoChildRef"
            @goToProfile="openProfile"
            @goToSubscription="openSubscription"
            @openModal="openVideo"
            @error="loadError = String($event || '')"
            @loading-change="isRefreshing = !!$event"
          />
        </keep-alive>
      </router-view>
    </div>
  </AppPageShell>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useRouteTabSync } from '../composables/useRouteTabSync'
import { useFeedFilters } from '../composables/useFeedFilters'
import { useRefreshTriggers } from '../composables/useRefreshTriggers'
import FeedToolbar from '@/features/video/components/feed/FeedToolbar.vue'
import CreatorHeader from '@/features/video/components/feed/CreatorHeader.vue'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import { Button } from '@/shared/ui/button'
import { VIDEO_TABS } from '@/features/video/constants/videos'
import { useVideoCardNavigation } from '@/features/video/composables/useVideoCardNavigation'
import type { CreatorDetail } from '@/features/video/types/creator'

defineOptions({ name: 'CreatorDetailView' })

const router = useRouter()
const route = useRoute()
const { openVideo, openSubscription, openProfile } = useVideoCardNavigation(router)

const creatorId = computed(() => route.params.id as string)
const { activeTab, nsfw, sortBy, special, timeRange, duration, contentType, filters } = useFeedFilters({
  creatorIdRef: creatorId,
})

const tabs = ref(VIDEO_TABS)
const isRefreshing = ref(false)
const loadError = ref<string | null>(null)
const videoChildRef = ref<{ refresh?: () => void } | null>(null)
const creatorDetail = ref<CreatorDetail | null>(null)

const childFilters = computed(() => filters.value)

const refreshCurrentList = () => {
  loadError.value = null
  videoChildRef.value?.refresh?.()
}

const setSpecialFilter = (value: string) => {
  special.value = value === 'yes' ? 'yes' : 'all'
  const query = { ...route.query }
  if (special.value === 'yes') query.special = 'yes'
  else delete query.special
  router.replace({ query })
}

useRefreshTriggers({ onRefresh: refreshCurrentList })
useRouteTabSync(router, route, activeTab, undefined, creatorId)

watch(() => route.query.special, (value) => {
  special.value = value === 'yes' ? 'yes' : 'all'
}, { immediate: true })
</script>

<style scoped>
.creator-detail-page {
  --app-page-max-width: var(--app-content-media-max);
}
</style>
