<template>
  <section class="feed-toolbar" :class="`feed-toolbar--${variant}`">
    <div class="feed-toolbar__primary">
      <AppTextTabs
        v-if="showTabs"
        :model-value="localActiveTab"
        class="feed-toolbar__tabs no-scrollbar"
        :options="tabs"
        aria-label="视频分类"
        @update:model-value="setActiveTab"
      />
      <slot name="after-tabs" />
    </div>

    <div class="feed-toolbar__actions">
      <template v-if="showFilter">
        <PopoverRoot>
          <PopoverTrigger as-child>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="app-filter-toolbar-button"
            :class="{ 'is-active': activeFilterCount > 0 }"
            :aria-label="filterButtonLabel"
          >
            <span>筛选</span>
            <span
              v-if="activeFilterCount > 0"
              class="app-filter-toolbar-button__count app-mono"
            >
              {{ activeFilterCount }}
            </span>
          </Button>
          </PopoverTrigger>

        <PopoverContent class="app-filter-popover">
          <AppFilterPanel
            :active-count="activeFilterCount"
            @reset="clearAllFilters"
          >
            <AppFilterSection v-if="!subscriptionId" label="来源">
              <AppFilterOptionList
                :model-value="site || 'all'"
                :options="siteFilterOptions"
                label="按来源筛选"
                @update:model-value="handleSiteChange"
              >
                <template #leading="{ option }">
                  <span
                    v-if="option.value === 'all'"
                    class="app-filter-all-icon"
                    aria-hidden="true"
                  >
                    <AppIcon name="layoutGrid" />
                  </span>
                  <SiteIcon
                    v-else
                    :site="option.value"
                    :icon-url="option.iconUrl"
                    :label="option.label"
                    size="sm"
                    rounded="sm"
                  />
                </template>
              </AppFilterOptionList>
            </AppFilterSection>

            <AppFilterSection label="时间" layout="row" divided>
              <AppSegmentedControl
                :model-value="timeRange"
                :options="timeRangeOptions"
                aria-label="按时间范围筛选"
                size="sm"
                fill
                @update:model-value="handleTimeRangeChange"
              />
            </AppFilterSection>

            <AppFilterSection label="时长" layout="row">
              <AppSegmentedControl
                :model-value="duration"
                :options="durationOptions"
                aria-label="按视频时长筛选"
                size="sm"
                fill
                @update:model-value="handleDurationChange"
              />
            </AppFilterSection>

            <AppFilterSection v-if="!subscriptionId" label="类型" layout="row">
              <AppSegmentedControl
                :model-value="contentType"
                :options="contentTypeOptions"
                aria-label="按来源类型筛选"
                size="sm"
                fill
                @update:model-value="handleContentTypeChange"
              />
            </AppFilterSection>

            <AppFilterSection v-if="settings.showNsfw" label="分级" layout="row">
              <AppSegmentedControl
                :model-value="nsfw"
                :options="nsfwOptions"
                aria-label="按内容分级筛选"
                size="sm"
                fill
                @update:model-value="handleNsfwChange"
              />
            </AppFilterSection>

            <label
              v-if="!subscriptionId"
              class="app-filter-toggle"
              :class="{ 'is-active': special === 'yes' }"
            >
              <span class="app-filter-toggle__copy">
                <span class="app-filter-toggle__title">特别关注</span>
              </span>
              <Switch
                :model-value="special === 'yes'"
                aria-label="只显示特别关注频道的视频"
                @update:model-value="handleSpecialChange"
              />
            </label>
          </AppFilterPanel>
        </PopoverContent>
        </PopoverRoot>
      </template>

      <!-- A single sort mode is a label, not an interactive control. -->

      <div class="feed-toolbar__group" role="group" aria-label="列表工具">
        <span v-if="showSort && !hasMultipleSortOptions" class="feed-toolbar__sort-label">最新</span>
        <Select
          v-else-if="showSort"
          v-model="localSortBy"
          :options="sortOptions"
          option-label="label"
          option-value="value"
          size="small"
          class="app-toolbar-control app-toolbar-select-trigger min-w-36"
          :class="{ 'is-active': localSortBy !== 'publish_date' }"
          aria-label="视频排序"
        />

        <AppSegmentedControl
          :model-value="uiStore.viewMode"
          :options="viewModeOptions"
          aria-label="视频视图"
          size="icon"
          class="feed-toolbar__view-mode"
          @update:model-value="handleViewModeChange"
        >
          <template #option="{ option }">
            <AppIcon v-if="option.icon" :name="option.icon" class="h-4 w-4" />
          </template>
        </AppSegmentedControl>

        <AppSegmentedControl
          v-if="variant === 'workbench' && uiStore.viewMode === 'grid'"
          :model-value="uiStore.videoDensity"
          :options="densityOptions"
          aria-label="缩略图密度"
          size="icon"
          class="feed-toolbar__density"
          @update:model-value="handleDensityChange"
        >
          <template #option="{ option }">
            <span class="feed-toolbar__density-mark" :class="`is-${option.value}`" />
          </template>
        </AppSegmentedControl>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import AppFilterOptionList from '@/shared/components/layout/AppFilterOptionList.vue'
import AppFilterPanel from '@/shared/components/layout/AppFilterPanel.vue'
import AppFilterSection from '@/shared/components/layout/AppFilterSection.vue'
import AppTextTabs from '@/shared/components/layout/AppTextTabs.vue'
import type { TimeRange, Duration, ContentType } from '@/features/video/composables/useFeedFilters'
import { useSites } from '@/features/video/composables/useSites'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import { Button } from '@/shared/ui/button'
import { PopoverContent, PopoverRoot, PopoverTrigger } from '@/shared/ui/popover'
import { Select } from '@/shared/ui/select'
import { Switch } from '@/shared/ui/switch'
import { useUIStore } from '@/shared/stores/ui'
import type { VideoTab } from '@/features/video/constants/videos'
import {
  CONTENT_TYPE_OPTIONS,
  DURATION_OPTIONS,
  NSFW_OPTIONS,
  SORT_OPTIONS,
  TIME_RANGE_OPTIONS,
} from '@/features/video/constants/feedFilters'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'

const props = withDefaults(defineProps<{
  activeTab?: string
  nsfw?: string
  sortBy?: string
  site?: string
  subscriptionId?: string | number
  tabs?: VideoTab[]
  showTabs?: boolean
  showSort?: boolean
  showFilter?: boolean
  timeRange?: TimeRange
  duration?: Duration
  contentType?: ContentType
  special?: string
  variant?: 'default' | 'workbench'
  preferenceKey?: string
}>(), {
  activeTab: 'all',
  nsfw: 'all',
  sortBy: 'publish_date',
  tabs: () => [],
  showTabs: true,
  showSort: true,
  showFilter: true,
  timeRange: 'all',
  duration: 'all',
  contentType: 'all',
  special: 'all',
  variant: 'default',
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
])

const { options: siteOptions, fetchSites } = useSites()
const { settings, loadUserSettings } = useUserSettings()
const uiStore = useUIStore()

onMounted(async () => {
  await Promise.all([fetchSites(), loadUserSettings()])
})

const localActiveTab = ref(props.activeTab)
const setActiveTab = (value: string | number) => {
  localActiveTab.value = String(value)
}
const localSortBy = ref(props.sortBy)

const handleSiteChange = (value: string) => {
  emit('update:site', value === 'all' ? '' : value)
}

const handleTimeRangeChange = (value: string | number) => {
  if (typeof value === 'string') emit('update:timeRange', value as TimeRange)
}

const handleDurationChange = (value: string | number) => {
  if (typeof value === 'string') emit('update:duration', value as Duration)
}

const handleContentTypeChange = (value: string | number) => {
  if (typeof value === 'string') emit('update:contentType', value as ContentType)
}

const handleNsfwChange = (value: string | number) => {
  if (typeof value === 'string') emit('update:nsfw', value)
}

const visibleSiteOptions = computed(() => (
  (siteOptions.value ?? []).filter((option) => settings.value.showNsfw || option.isNsfw !== true)
))

const siteFilterOptions = computed(() => [
  {
    value: 'all',
    label: '全部来源',
    iconUrl: null as string | null,
  },
  ...visibleSiteOptions.value.map((option) => ({
    value: option.value,
    label: option.label,
    iconUrl: option.iconUrl ?? null,
  })),
])

const handleSpecialChange = (value: boolean) => {
  emit('update:special', value ? 'yes' : 'all')
}

const handleViewModeChange = (value: string | number) => {
  if (value !== 'grid' && value !== 'list') return
  uiStore.setViewMode(value, props.preferenceKey)
}

const handleDensityChange = (value: string | number) => {
  if (value !== 'compact' && value !== 'comfortable' && value !== 'large') return
  uiStore.setVideoDensity(value, props.preferenceKey)
}

const activeFilterCount = computed(() => {
  let count = 0
  if (!props.subscriptionId && props.site) count++
  if (props.timeRange !== 'all') count++
  if (props.duration !== 'all') count++
  if (!props.subscriptionId && props.contentType !== 'all') count++
  if (props.nsfw !== 'all') count++
  if (!props.subscriptionId && props.special === 'yes') count++
  return count
})

const filterButtonLabel = computed(() => (
  activeFilterCount.value > 0
    ? `筛选，已启用 ${activeFilterCount.value} 项`
    : '筛选'
))

const clearAllFilters = () => {
  if (!props.subscriptionId) emit('update:site', '')
  emit('update:timeRange', 'all')
  emit('update:duration', 'all')
  if (!props.subscriptionId) emit('update:contentType', 'all')
  emit('update:nsfw', 'all')
  if (!props.subscriptionId) emit('update:special', 'all')
}

watch(() => props.activeTab, (v) => { localActiveTab.value = v })
watch(() => props.sortBy, (v) => { localSortBy.value = v })
watch(
  () => props.preferenceKey,
  (key) => {
    if (key) uiStore.applyVideoViewPreference(key)
  },
  { immediate: true },
)
watch(localActiveTab, (v) => emit('update:activeTab', v))
watch(localSortBy, (v) => emit('update:sortBy', v))
watch(
  () => ({
    currentSite: props.site,
    showNsfw: settings.value.showNsfw,
    options: siteOptions.value ?? [],
  }),
  ({ currentSite, showNsfw, options }) => {
    if (!currentSite || showNsfw) return
    const selected = options.find((option) => option.value === currentSite)
    if (selected?.isNsfw === true) emit('update:site', '')
  },
  { immediate: true },
)

const sortOptions = SORT_OPTIONS
const hasMultipleSortOptions = sortOptions.length > 1
const timeRangeOptions = TIME_RANGE_OPTIONS
const durationOptions = DURATION_OPTIONS
const contentTypeOptions = CONTENT_TYPE_OPTIONS
const nsfwOptions = NSFW_OPTIONS
const viewModeOptions = [
  { value: 'grid', label: '网格视图', icon: 'layoutGrid' },
  { value: 'list', label: '列表视图', icon: 'list' },
] as const

const densityOptions = [
  { value: 'compact', label: '紧凑缩略图' },
  { value: 'comfortable', label: '标准缩略图' },
  { value: 'large', label: '大缩略图' },
] as const
</script>

<style scoped>
.feed-toolbar {
  position: relative;
  z-index: 10;
  display: flex;
  width: 100%;
  min-width: 0;
  min-height: 2.25rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
}

.feed-toolbar__primary {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: var(--space-5);
}

.feed-toolbar__tabs {
  min-width: 0;
  max-width: 100%;
  overflow-x: auto;
}

.feed-toolbar :deep(.app-segmented-control) {
  gap: 0.25rem;
  background: transparent;
  padding: 0;
}

.feed-toolbar :deep(.app-segmented-control__item) {
  color: hsl(var(--muted-foreground));
  background: transparent;
  box-shadow: none;
}

.feed-toolbar :deep(.app-segmented-control__item.is-active) {
  color: hsl(var(--foreground) / 0.82);
  background: transparent;
  box-shadow: none;
}

.feed-toolbar__actions {
  display: flex;
  flex: none;
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
  height: 1rem;
  background: var(--app-hairline);
}

.feed-toolbar--workbench {
  min-height: 2.75rem;
  gap: 1rem;
}

.feed-toolbar--workbench .feed-toolbar__primary {
  gap: 1rem;
}

.feed-toolbar--workbench .feed-toolbar__actions {
  gap: 0.375rem;
}

.feed-toolbar__density-mark {
  display: block;
  border: 1px solid currentColor;
  border-radius: 1px;
}

.feed-toolbar__density-mark.is-compact {
  width: 0.625rem;
  height: 0.625rem;
}

.feed-toolbar__density-mark.is-comfortable {
  width: 0.75rem;
  height: 0.75rem;
}

.feed-toolbar__density-mark.is-large {
  width: 0.875rem;
  height: 0.875rem;
}

@media (max-width: 980px) {
  .feed-toolbar--workbench {
    align-items: flex-start;
    flex-direction: column;
  }

  .feed-toolbar--workbench .feed-toolbar__actions {
    width: 100%;
    justify-content: flex-end;
  }
}

.feed-toolbar__sort-label {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-base);
  font-weight: 600;
  white-space: nowrap;
}
</style>
