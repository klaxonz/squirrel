<template>
  <section class="feed-toolbar">
    <div class="feed-toolbar__primary">
      <AppSectionNav
        v-if="showTabs"
        v-model="localActiveTab"
        class="feed-toolbar__tabs no-scrollbar"
        :options="tabs"
        aria-label="视频分类"
      />
      <slot name="after-tabs" />
    </div>

    <div class="feed-toolbar__actions">
      <template v-if="showFilter">
          <Button
            type="button"
            text severity="secondary"
            size="sm"
            class="app-filter-toolbar-button"
            :class="{ 'is-active': activeFilterCount > 0 }"
            :aria-label="filterButtonLabel"
            @click="toggleFilterPopover"
          >
            <AppIcon name="filter" class="h-3.5 w-3.5" />
            <span>筛选</span>
            <span
              v-if="activeFilterCount > 0"
              class="app-filter-toolbar-button__count app-mono"
            >
              {{ activeFilterCount }}
            </span>
          </Button>

        <PrimePopover
          ref="filterPopover"
          class="w-[17.25rem] overflow-hidden border-border/55 p-0 shadow-popover"
        >
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
                    class="feed-filter-all-icon"
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
              <AppFilterChips
                :model-value="timeRange"
                :options="timeRangeOptions"
                label="按时间范围筛选"
                @update:model-value="handleTimeRangeChange"
              />
            </AppFilterSection>

            <AppFilterSection label="时长" layout="row">
              <AppFilterChips
                :model-value="duration"
                :options="durationOptions"
                label="按视频时长筛选"
                @update:model-value="handleDurationChange"
              />
            </AppFilterSection>

            <AppFilterSection v-if="!subscriptionId" label="类型" layout="row">
              <AppFilterChips
                :model-value="contentType"
                :options="contentTypeOptions"
                label="按来源类型筛选"
                @update:model-value="handleContentTypeChange"
              />
            </AppFilterSection>

            <AppFilterSection v-if="settings.showNsfw" label="分级" layout="row">
              <AppFilterChips
                :model-value="nsfw"
                :options="nsfwOptions"
                label="按内容分级筛选"
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
        </PrimePopover>
      </template>

      <!--
        Consume toolbar stays light — sort + presentation live in the
        filter popover / a single overflow group, not a second Operate strip.
      -->
      <div
        v-if="showSort || showRefresh"
        class="feed-toolbar__divider"
        aria-hidden="true"
      />

      <div class="feed-toolbar__group" role="group" aria-label="列表工具">
        <PrimeSelect
          v-if="showSort"
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

        <Button
          v-if="showRefresh"
          type="button"
          text severity="secondary"
          size="sm" icon-only
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
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import AppFilterChips from '@/shared/components/layout/AppFilterChips.vue'
import AppFilterOptionList from '@/shared/components/layout/AppFilterOptionList.vue'
import AppFilterPanel from '@/shared/components/layout/AppFilterPanel.vue'
import AppFilterSection from '@/shared/components/layout/AppFilterSection.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import type { TimeRange, Duration, ContentType } from '@/features/video/composables/useFeedFilters'
import { useSites } from '@/features/video/composables/useSites'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import { Button } from '@/shared/ui/button'
import PrimePopover from 'primevue/popover'
import PrimeSelect from 'primevue/select'
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

const filterPopover = ref<{ toggle: (event: Event) => void } | null>(null)
const toggleFilterPopover = (event: Event) => filterPopover.value?.toggle(event)

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
const { settings, loadUserSettings } = useUserSettings()
const uiStore = useUIStore()

onMounted(async () => {
  await Promise.all([fetchSites(), loadUserSettings()])
})

const localActiveTab = ref(props.activeTab)
const localSortBy = ref(props.sortBy)

const handleSiteChange = (value: string) => {
  emit('update:site', value === 'all' ? '' : value)
}

const handleTimeRangeChange = (value: string) => {
  emit('update:timeRange', value as TimeRange)
}

const handleDurationChange = (value: string) => {
  emit('update:duration', value as Duration)
}

const handleContentTypeChange = (value: string) => {
  emit('update:contentType', value as ContentType)
}

const handleNsfwChange = (value: string) => {
  emit('update:nsfw', value)
}

const SITE_SHORT_LABELS: Record<string, string> = {
  bilibili: 'B站',
  youtube: '油管',
  javdb: 'JavDB',
  pornhub: 'PH',
  youporn: 'YP',
}

const visibleSiteOptions = computed(() => (
  (siteOptions.value ?? []).filter((option) => settings.value.showNsfw || option.isNsfw !== true)
))

const siteFilterOptions = computed(() => [
  {
    value: 'all',
    label: '全部来源',
    shortLabel: '全部',
    iconUrl: null as string | null,
  },
  ...visibleSiteOptions.value.map((option) => ({
    value: option.value,
    label: option.label,
    shortLabel: SITE_SHORT_LABELS[option.value.toLowerCase()] || option.label,
    iconUrl: option.iconUrl ?? null,
  })),
])

const handleSpecialChange = (value: boolean) => {
  emit('update:special', value ? 'yes' : 'all')
}

const handleViewModeChange = (value: string | number) => {
  if (value !== 'grid' && value !== 'list') return
  uiStore.setViewMode(value)
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
const timeRangeOptions = TIME_RANGE_OPTIONS
const durationOptions = DURATION_OPTIONS
const contentTypeOptions = CONTENT_TYPE_OPTIONS
const nsfwOptions = NSFW_OPTIONS

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

.feed-filter-all-icon {
  display: inline-flex;
  width: 1.5rem;
  height: 1.5rem;
  align-items: center;
  justify-content: center;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--radius-sm);
  background: hsl(var(--background));
  color: hsl(var(--foreground) / 0.72);
}

.feed-filter-all-icon :deep(svg) {
  width: 0.8125rem;
  height: 0.8125rem;
}

</style>
