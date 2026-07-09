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
            class="feed-toolbar__tab"
            :class="{ 'is-active': localActiveTab === tab.value }"
            @click="localActiveTab = tab.value"
          >
            {{ tab.label }}
          </Button>
        </div>
        <div v-if="canScrollLeft" class="feed-toolbar__fade feed-toolbar__fade--left" />
        <div v-if="canScrollRight" class="feed-toolbar__fade feed-toolbar__fade--right" />
      </nav>
    </div>

    <div class="feed-toolbar__actions">
      <!-- Filters: active chips + site + more-filters -->
      <div class="feed-toolbar__group" role="group" aria-label="筛选">
        <Button
          v-for="chip in activeFilterChips"
          :key="chip.key"
          type="button"
          variant="outline"
          size="sm"
          class="app-toolbar-control app-toolbar-chip app-toolbar-chip--active"
          :title="chip.clearTitle"
          :aria-label="chip.clearTitle"
          @click="chip.clear"
        >
          <AppIcon v-if="chip.icon" :name="chip.icon" class="h-3.5 w-3.5" :class="chip.iconClass" />
          <span>{{ chip.label }}</span>
          <AppIcon name="close" class="h-3 w-3 opacity-70" />
        </Button>

        <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
          <SelectTrigger
            class="app-toolbar-control app-toolbar-select-trigger"
            :class="{ 'is-active': !!site }"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent class="min-w-44 rounded-md border-border/60 bg-popover shadow-lg">
            <SelectItem value="all" class="text-xs">全部站点</SelectItem>
            <SelectItem
              v-for="opt in siteOptions"
              :key="opt.value"
              :value="opt.value"
              class="text-xs"
            >
              {{ opt.label }}
            </SelectItem>
          </SelectContent>
        </Select>

        <Button
          v-if="showFilter"
          type="button"
          variant="ghost"
          size="icon-sm"
          class="app-toolbar-control app-toolbar-icon-button"
          :class="{ 'is-active': hiddenFilterCount > 0 }"
          :title="filterButtonTitle"
          :aria-label="filterButtonTitle"
          @click="filterModalOpen = true"
        >
          <AppIcon name="filter" class="size-4 shrink-0" />
        </Button>
      </div>

      <div v-if="showSort" class="feed-toolbar__divider" aria-hidden="true" />

      <!-- Sort: separate from filters, labels read as order criteria -->
      <div v-if="showSort" class="feed-toolbar__group" role="group" aria-label="排序">
        <Select v-model="localSortBy">
          <SelectTrigger
            class="app-toolbar-control app-toolbar-select-trigger"
            :class="{ 'is-active': localSortBy !== 'publish_date' }"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent class="min-w-36 rounded-md border-border/60 bg-popover shadow-lg">
            <SelectItem
              v-for="opt in sortOptions"
              :key="opt.value"
              :value="opt.value"
              class="text-xs"
            >
              {{ opt.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div class="feed-toolbar__divider" aria-hidden="true" />

      <!-- Presentation: view mode + refresh -->
      <div class="feed-toolbar__group" role="group" aria-label="视图">
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
          title="刷新内容"
          aria-label="刷新内容"
          @click="$emit('refresh')"
        >
          <AppSpinner v-if="isRefreshing" size="sm" />
          <AppIcon
            v-else
            name="refresh"
            class="w-4 h-4 shrink-0"
          />
        </Button>
      </div>
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
      :scope="props.filterScope"
      @update:time-range="(v) => emit('update:timeRange', v)"
      @update:duration="(v) => emit('update:duration', v)"
      @update:content-type="(v) => emit('update:contentType', v)"
      @update:nsfw="(v) => emit('update:nsfw', v)"
      @update:site="(v) => emit('update:site', v)"
    />
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import FilterModal from './FilterModal.vue'
import type { TimeRange, Duration, ContentType } from '@/features/video/composables/useFeedFilters'
import { useSites } from '@/features/video/composables/useSites'
import { Button } from '@/shared/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
import { useUIStore } from '@/shared/stores/ui'
import type { VideoTab } from '@/features/video/constants/videos'
import {
  CONTENT_TYPE_OPTIONS,
  DURATION_OPTIONS,
  NSFW_OPTIONS,
  SORT_OPTIONS,
  TIME_RANGE_OPTIONS,
  labelForOption,
} from '@/features/video/constants/feedFilters'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'

type ActiveFilterChip = {
  key: string
  label: string
  clearTitle: string
  icon?: AppIconName
  iconClass?: string
  clear: () => void
}

const props = withDefaults(defineProps<{
  activeTab?: string
  nsfw?: string
  sortBy?: string
  site?: string
  subscriptionId?: string | number
  tabs?: VideoTab[]
  isRefreshing?: boolean
  showTabs?: boolean
  showSort?: boolean
  showRefresh?: boolean
  showFilter?: boolean
  timeRange?: TimeRange
  duration?: Duration
  contentType?: ContentType
  special?: string
  siteLabel?: string
  filterScope?: 'video' | 'subscription'
}>(), {
  activeTab: 'all',
  nsfw: 'all',
  sortBy: 'publish_date',
  tabs: () => [],
  isRefreshing: false,
  showTabs: true,
  showSort: true,
  showRefresh: true,
  showFilter: true,
  timeRange: 'all',
  duration: 'all',
  contentType: 'all',
  special: 'all',
  filterScope: 'video',
})

const emit = defineEmits([
  'update:activeTab',
  'update:nsfw',
  'update:sortBy',
  'update:site',
  'update:timeRange',
  'update:duration',
  'update:contentType',
  'update:special',
  'refresh',
])

const { options: siteOptions, fetchSites } = useSites()
const uiStore = useUIStore()

onMounted(() => {
  fetchSites()
  nextTick(updateScrollState)
})

const localActiveTab = ref(props.activeTab)
const localSortBy = ref(props.sortBy)
const filterModalOpen = ref(false)

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

/**
 * Modal-owned dimensions only (time, duration, content type, nsfw).
 * Special / site / sort live in toolbar chrome and are never mixed in here.
 * Active values also render as dismissible chips — funnel uses is-active only,
 * not a numeric badge (avoids double-counting).
 */
const hiddenFilterCount = computed(() => {
  let c = 0
  if (props.timeRange !== 'all') c++
  if (props.duration !== 'all') c++
  if (!props.subscriptionId && props.contentType !== 'all') c++
  if (props.nsfw !== 'all') c++
  return c
})

const filterButtonTitle = computed(() => (
  hiddenFilterCount.value > 0
    ? `更多筛选（${hiddenFilterCount.value} 项已启用）`
    : '更多筛选'
))

/**
 * Dismissible chips for active non-default filters that would otherwise only
 * live in the modal or as a boolean toggle. Site stays a Select (shows value +
 * can reset to 全部站点). Sort is not a filter chip.
 */
const activeFilterChips = computed<ActiveFilterChip[]>(() => {
  const chips: ActiveFilterChip[] = []

  if (!props.subscriptionId && props.special === 'yes') {
    chips.push({
      key: 'special',
      label: '特别关注',
      clearTitle: '清除特别关注过滤',
      icon: 'star',
      iconClass: 'fill-current',
      clear: () => emit('update:special', 'all'),
    })
  }

  if (props.timeRange !== 'all') {
    chips.push({
      key: 'timeRange',
      label: labelForOption(TIME_RANGE_OPTIONS, props.timeRange),
      clearTitle: '清除时间筛选',
      clear: () => emit('update:timeRange', 'all'),
    })
  }

  if (props.duration !== 'all') {
    chips.push({
      key: 'duration',
      label: labelForOption(DURATION_OPTIONS, props.duration),
      clearTitle: '清除时长筛选',
      clear: () => emit('update:duration', 'all'),
    })
  }

  if (!props.subscriptionId && props.contentType !== 'all') {
    chips.push({
      key: 'contentType',
      label: labelForOption(CONTENT_TYPE_OPTIONS, props.contentType),
      clearTitle: '清除来源类型筛选',
      clear: () => emit('update:contentType', 'all'),
    })
  }

  if (props.nsfw !== 'all') {
    chips.push({
      key: 'nsfw',
      label: labelForOption(NSFW_OPTIONS, props.nsfw),
      clearTitle: '清除内容分级筛选',
      clear: () => emit('update:nsfw', 'all'),
    })
  }

  return chips
})

watch(() => props.activeTab, (v) => { localActiveTab.value = v })
watch(() => props.sortBy, (v) => { localSortBy.value = v })
watch(localActiveTab, (v) => emit('update:activeTab', v))
watch(localSortBy, (v) => emit('update:sortBy', v))
watch(() => props.tabs, () => nextTick(updateScrollState), { deep: true })
watch(() => tabsScroll.value?.scrollWidth, () => nextTick(updateScrollState))

const sortOptions = SORT_OPTIONS

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
  gap: var(--space-3);
}

.feed-toolbar__primary {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
}

.feed-toolbar__tabs {
  position: relative;
  min-width: 0;
  max-width: 100%;
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
  background: hsl(var(--secondary) / 0.72);
}

.feed-toolbar__tab {
  flex: 0 0 auto;
  height: 2rem;
  padding: 0 var(--space-3);
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
}

.feed-toolbar__tab:hover {
  color: hsl(var(--foreground));
}

.feed-toolbar__tab.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--card));
  box-shadow: var(--shadow-xs);
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
  flex: 0 1 auto;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
  margin-left: auto;
}

.feed-toolbar__group {
  display: flex;
  flex: 0 1 auto;
  align-items: center;
  gap: var(--space-2);
  min-width: 0;
}

.feed-toolbar__divider {
  flex: 0 0 auto;
  width: 1px;
  height: 1.25rem;
  background: hsl(var(--border) / 0.7);
}
</style>
