<template>
  <section class="feed-toolbar">
    <div class="feed-toolbar__primary">
      <nav v-if="showTabs" class="feed-toolbar__tabs" aria-label="视频分类">
        <div
          ref="tabsScroll"
          class="feed-toolbar__tabs-scroll no-scrollbar"
          @scroll="updateScrollState"
        >
          <Button
            v-for="tab in tabs"
            :key="tab.value"
            variant="ghost"
            size="sm"
            class="feed-toolbar__tab app-tab-button"
            :class="{ 'is-active': localActiveTab === tab.value }"
            @click="localActiveTab = tab.value"
          >
            {{ tab.label }}
          </Button>
        </div>
        <div v-if="canScrollLeft" class="feed-toolbar__fade feed-toolbar__fade--left"></div>
        <div v-if="canScrollRight" class="feed-toolbar__fade feed-toolbar__fade--right"></div>
      </nav>
    </div>

    <div class="feed-toolbar__actions">
      <Button
        v-if="special === 'yes'"
        type="button"
        variant="outline"
        size="sm"
        class="app-toolbar-control app-toolbar-chip app-toolbar-chip--warning"
        title="清除特别关注过滤"
        @click="emit('update:special', 'all')"
      >
        <AppIcon name="star" class="h-3.5 w-3.5 fill-current" />
        特别关注
        <AppIcon name="close" class="h-3 w-3" />
      </Button>

      <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
        <SelectTrigger class="app-toolbar-control app-toolbar-select-trigger">
          <SelectValue />
        </SelectTrigger>
          <SelectContent class="min-w-44 rounded-md border-border/60 bg-popover shadow-lg">
          <SelectItem value="all" class="text-xs">全部站点</SelectItem>
          <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">
            {{ opt.label }}
          </SelectItem>
        </SelectContent>
      </Select>

      <div v-if="showSort" class="hidden sm:block shrink-0">
        <Select v-model="localSortBy">
          <SelectTrigger class="app-toolbar-control app-toolbar-select-trigger">
            <SelectValue />
          </SelectTrigger>
          <SelectContent class="min-w-36 rounded-md border-border/60 bg-popover shadow-lg">
            <SelectItem v-for="opt in sortOptions" :key="opt.value" :value="opt.value" class="text-xs">
              {{ opt.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <Button
        v-if="showFilter"
        type="button"
        variant="ghost"
        size="icon-sm"
        class="app-toolbar-control app-toolbar-icon-button"
        :class="[
          activeFilterCount > 0
            ? 'is-active'
            : ''
        ]"
        @click="filterModalOpen = true"
        :title="activeFilterCount > 0 ? '筛选已启用' : '筛选'"
        :aria-label="activeFilterCount > 0 ? '筛选已启用' : '筛选'"
      >
        <AppIcon name="filter" class="size-4 shrink-0" />
        <span
          v-if="activeFilterCount > 0"
          class="app-toolbar-count"
        >{{ activeFilterCount }}</span>
      </Button>

      <AppSegmentedControl
        :model-value="uiStore.viewMode"
        :options="viewModeOptions"
        aria-label="视频视图"
        size="icon"
        @update:model-value="handleViewModeChange"
      >
        <template #option="{ option }">
          <AppIcon v-if="option.icon" :name="option.icon" class="h-4 w-4" />
        </template>
      </AppSegmentedControl>
      <Button
        v-if="showRefresh"
        type="button"
        variant="ghost"
        size="icon-sm"
        class="app-toolbar-control app-toolbar-icon-button"
        @click="$emit('refresh')"
        title="刷新内容"
        aria-label="刷新内容"
      >
        <AppSpinner v-if="isRefreshing" size="sm" />
        <AppIcon
          v-else
          name="refresh"
          class="w-4 h-4 shrink-0"
        />
      </Button>
    </div>

    <FilterModal
      v-if="filterModalOpen"
      :model-value="filterModalOpen"
      @update:modelValue="filterModalOpen = $event"
      :time-range="timeRange"
      :duration="duration"
      :content-type="contentType"
      :nsfw="nsfw"
      :site="site"
      :subscription-id="subscriptionId"
      :site-label="siteLabel"
      :sort-by="localSortBy"
      :scope="props.filterScope"
      @update:time-range="(v) => emit('update:timeRange', v)"
      @update:duration="(v) => emit('update:duration', v)"
      @update:content-type="(v) => emit('update:contentType', v)"
      @update:nsfw="(v) => emit('update:nsfw', v)"
      @update:site="(v) => emit('update:site', v)"
      @update:sort-by="(v) => localSortBy = v"
    />
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import FilterModal from './FilterModal.vue'
import type { TimeRange, Duration, ContentType } from '@/features/video/composables/useFeedFilters'
import { useSites } from '@/features/video/composables/useSites'
import { Button } from '@/shared/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import { useUIStore } from '@/shared/stores/ui'
import type { VideoTab } from '@/features/video/constants/videos'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'

const props = withDefaults(defineProps<{
  activeTab?: string, nsfw?: string, sortBy?: string, site?: string, subscriptionId?: string | number,
  tabs?: VideoTab[], isRefreshing?: boolean, showTabs?: boolean, showSort?: boolean, showRefresh?: boolean,
  showFilter?: boolean, timeRange?: TimeRange, duration?: Duration, contentType?: ContentType,
  special?: string, siteLabel?: string, filterScope?: 'video' | 'subscription'
}>(), {
  activeTab: 'all', nsfw: 'all', sortBy: 'publish_date', tabs: () => [], isRefreshing: false,
  showTabs: true, showSort: true, showRefresh: true, showFilter: true,
  timeRange: 'all', duration: 'all', contentType: 'all', special: 'all', filterScope: 'video',
})

const emit = defineEmits([
  'update:activeTab', 'update:nsfw', 'update:sortBy', 'update:site',
  'update:timeRange', 'update:duration', 'update:contentType', 'update:special', 'refresh',
])

const { options: siteOptions, fetchSites } = useSites()

onMounted(() => {
  fetchSites()
  nextTick(updateScrollState)
})

const localActiveTab = ref(props.activeTab)
const localSortBy = ref(props.sortBy)
const filterModalOpen = ref(false)

// Tab overflow fade hints: only show the edge fade on a side that can scroll further.
const tabsScroll = ref<HTMLElement | null>(null)
const canScrollLeft = ref(false)
const canScrollRight = ref(false)

const updateScrollState = () => {
  const el = tabsScroll.value
  if (!el) return
  canScrollLeft.value = el.scrollLeft > 0
  canScrollRight.value = el.scrollLeft < el.scrollWidth - el.clientWidth - 2
}

const handleSiteChange = (val: unknown) => emit('update:site', val === 'all' ? '' : val)

const handleViewModeChange = (value: string | number) => {
  if (value !== 'grid' && value !== 'list') return
  uiStore.setViewMode(value)
}

const activeFilterCount = computed(() => {
  let c = 0
  if (localSortBy.value !== 'publish_date') c++
  if (props.timeRange !== 'all') c++
  if (props.duration !== 'all') c++
  if (!props.subscriptionId && props.contentType !== 'all') c++
  if (!props.subscriptionId && props.special !== 'all') c++
  if (props.nsfw !== 'all') c++
  if (props.site) c++
  return c
})

watch(() => props.activeTab, (v) => { localActiveTab.value = v })
watch(() => props.sortBy, (v) => { localSortBy.value = v })
watch(localActiveTab, (v) => emit('update:activeTab', v))
watch(localSortBy, (v) => emit('update:sortBy', v))
// Re-measure overflow state when tabs change or layout settles.
watch(() => props.tabs, () => nextTick(updateScrollState), { deep: true })
watch(() => tabsScroll.value?.scrollWidth, () => nextTick(updateScrollState))

const uiStore = useUIStore()

const sortOptions = [
  { value: 'publish_date', label: '上传日期' },
  { value: 'created_at', label: '抓取日期' },
]

const viewModeOptions = [
  { value: 'grid', label: '网格视图', icon: 'layoutGrid' },
  { value: 'list', label: '列表视图', icon: 'list' },
] as const

</script>

<style scoped>
.feed-toolbar {
  position: relative;
  z-index: 10;
  display: flex;
  width: 100%;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.feed-toolbar__primary {
  min-width: 0;
  display: flex;
  align-items: center;
}

.feed-toolbar__tabs {
  position: relative;
  min-width: 0;
}

.feed-toolbar__tabs-scroll {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  padding: 2px;
  border: 1px solid hsl(var(--border) / 0.58);
  border-radius: var(--radius-lg);
  background: hsl(var(--background) / 0.52);
}

.feed-toolbar__tab {
  flex: 0 0 auto;
  height: 2rem;
  padding: 0 var(--space-3);
  font-size: 0.8125rem;
  font-weight: 650;
}

.feed-toolbar__fade {
  pointer-events: none;
  position: absolute;
  top: 2px;
  bottom: 2px;
  width: 1.25rem;
}

.feed-toolbar__fade--left {
  left: 2px;
  background: linear-gradient(to right, hsl(var(--background)), transparent);
}

.feed-toolbar__fade--right {
  right: 2px;
  background: linear-gradient(to left, hsl(var(--background)), transparent);
}

.feed-toolbar__actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
  white-space: nowrap;
}

</style>
