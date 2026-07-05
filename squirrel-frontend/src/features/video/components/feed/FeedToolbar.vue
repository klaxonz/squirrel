<template>
  <section class="feed-toolbar">
    <div class="feed-toolbar__primary">
      <nav v-if="showTabs" class="feed-toolbar__tabs" aria-label="视频分类">
        <div
          ref="tabsScroll"
          class="feed-toolbar__tabs-scroll no-scrollbar"
          @scroll="updateScrollState"
        >
          <button
            v-for="tab in tabs"
            :key="tab.value"
            class="feed-toolbar__tab"
            :class="{ 'is-active': localActiveTab === tab.value }"
            @click="localActiveTab = tab.value"
          >
            {{ tab.label }}
          </button>
        </div>
        <div v-if="canScrollLeft" class="feed-toolbar__fade feed-toolbar__fade--left"></div>
        <div v-if="canScrollRight" class="feed-toolbar__fade feed-toolbar__fade--right"></div>
      </nav>
    </div>

    <div class="feed-toolbar__actions">
      <button
        v-if="special === 'yes'"
        type="button"
        class="feed-toolbar__chip feed-toolbar__chip--warning"
        title="清除特别关注过滤"
        @click="emit('update:special', 'all')"
      >
        <AppIcon name="star" class="h-3.5 w-3.5 fill-current" />
        特别关注
        <AppIcon name="close" class="h-3 w-3" />
      </button>

      <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
        <SelectTrigger class="feed-toolbar__select-trigger">
          <SelectValue />
        </SelectTrigger>
        <SelectContent class="min-w-44 border-border/60 bg-popover shadow-lg rounded-md">
          <SelectItem value="all" class="text-xs">全部站点</SelectItem>
          <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">
            {{ opt.label }}
          </SelectItem>
        </SelectContent>
      </Select>

      <div v-if="showSort" class="hidden sm:block shrink-0">
        <Select v-model="localSortBy">
          <SelectTrigger class="feed-toolbar__select-trigger">
            <SelectValue />
          </SelectTrigger>
          <SelectContent class="min-w-36 border-border/60 bg-popover shadow-lg rounded-md">
            <SelectItem v-for="opt in sortOptions" :key="opt.value" :value="opt.value" class="text-xs">
              {{ opt.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <button
        v-if="showFilter"
        type="button"
        class="feed-toolbar__icon-button"
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
          class="feed-toolbar__count"
        >{{ activeFilterCount }}</span>
      </button>

      <div class="feed-toolbar__view-toggle">
        <button
          class="feed-toolbar__view-button"
          :class="{ 'is-active': uiStore.viewMode === 'grid' }"
          @click="uiStore.setViewMode('grid')"
          title="网格视图"
          aria-label="网格视图"
        >
          <AppIcon name="layoutGrid" class="w-4 h-4" />
        </button>
        <button
          class="feed-toolbar__view-button"
          :class="{ 'is-active': uiStore.viewMode === 'list' }"
          @click="uiStore.setViewMode('list')"
          title="列表视图"
          aria-label="列表视图"
        >
          <AppIcon name="list" class="w-4 h-4" />
        </button>
      </div>

      <button
        v-if="showRefresh"
        type="button"
        class="feed-toolbar__icon-button"
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
      </button>
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
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import { useUIStore } from '@/shared/stores/ui'
import type { VideoTab } from '@/features/video/constants/videos'

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
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: hsl(var(--muted-foreground));
  font-size: 0.8125rem;
  font-weight: 650;
  white-space: nowrap;
  outline: none;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    box-shadow var(--duration-fast) var(--ease-default);
}

.feed-toolbar__tab:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent) / 0.58);
}

.feed-toolbar__tab:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.36);
}

.feed-toolbar__tab.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--card));
  box-shadow: 0 0 0 1px hsl(var(--border) / 0.5);
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

.feed-toolbar__chip,
.feed-toolbar__select-trigger,
.feed-toolbar__icon-button,
.feed-toolbar__view-toggle {
  border: 1px solid hsl(var(--border) / 0.58);
  border-radius: var(--radius-md);
  background: hsl(var(--background) / 0.36);
  color: hsl(var(--muted-foreground));
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default);
}

.feed-toolbar__chip {
  display: inline-flex;
  height: 2rem;
  align-items: center;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  font-size: 0.75rem;
  font-weight: 650;
}

.feed-toolbar__chip--warning {
  border-color: hsl(var(--warning) / 0.38);
  background: hsl(var(--warning) / 0.1);
  color: hsl(var(--warning));
}

:deep(.feed-toolbar__select-trigger) {
  height: 2rem;
  width: auto;
  min-width: 0;
  flex-shrink: 0;
  flex-wrap: nowrap;
  gap: var(--space-2);
  padding: 0 var(--space-3);
  box-shadow: none;
  font-size: 0.75rem;
  font-weight: 650;
  white-space: nowrap;
}

:deep(.feed-toolbar__select-trigger:hover),
.feed-toolbar__icon-button:hover,
.feed-toolbar__view-button:hover {
  color: hsl(var(--foreground));
  border-color: hsl(var(--border));
  background: hsl(var(--accent) / 0.58);
}

.feed-toolbar__icon-button {
  position: relative;
  display: inline-flex;
  width: 2rem;
  height: 2rem;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  outline: none;
}

.feed-toolbar__icon-button:focus-visible,
.feed-toolbar__view-button:focus-visible {
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.36);
}

.feed-toolbar__icon-button.is-active {
  color: hsl(var(--primary));
  border-color: hsl(var(--primary) / 0.28);
  background: hsl(var(--primary) / 0.12);
}

.feed-toolbar__count {
  position: absolute;
  top: -0.375rem;
  right: -0.375rem;
  display: inline-flex;
  min-width: 0.875rem;
  height: 0.875rem;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 0 0.25rem;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 0.5625rem;
  font-weight: 800;
  box-shadow: 0 0 0 2px hsl(var(--background));
}

.feed-toolbar__view-toggle {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
}

.feed-toolbar__view-button {
  display: inline-flex;
  width: 1.625rem;
  height: 1.625rem;
  align-items: center;
  justify-content: center;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: hsl(var(--muted-foreground));
  outline: none;
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.feed-toolbar__view-button.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--card));
}
</style>
