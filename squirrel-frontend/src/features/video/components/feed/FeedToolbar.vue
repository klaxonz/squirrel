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
    </div>

    <div class="feed-toolbar__actions">
      <Popover v-if="showFilter">
        <PopoverTrigger as-child>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            class="feed-toolbar__filter"
            :class="{ 'is-active': activeFilterCount > 0 }"
            :aria-label="filterButtonLabel"
          >
            <AppIcon name="filter" class="h-3.5 w-3.5" />
            <span>筛选</span>
            <span
              v-if="activeFilterCount > 0"
              class="feed-toolbar__filter-count app-mono"
            >
              {{ activeFilterCount }}
            </span>
          </Button>
        </PopoverTrigger>

        <PopoverContent align="end" :side-offset="8" class="w-80 p-0">
          <div class="feed-filter-panel">
            <header class="feed-filter-panel__header">
              <div>
                <strong>筛选</strong>
                <span>{{ filterDescription }}</span>
              </div>
              <Button
                v-if="activeFilterCount > 0"
                type="button"
                variant="ghost"
                size="xs"
                @click="clearAllFilters"
              >
                重置
              </Button>
            </header>

            <div class="feed-filter-panel__fields">
              <label v-if="!subscriptionId" class="feed-filter-panel__field">
                <span>来源</span>
                <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
                  <SelectTrigger aria-label="按来源筛选">
                    <SelectValue placeholder="全部来源" />
                  </SelectTrigger>
                  <SelectContent class="min-w-48">
                    <SelectItem value="all">全部来源</SelectItem>
                    <SelectItem
                      v-for="option in siteOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      <span class="feed-filter-panel__site-option">
                        <SiteIcon :site="option.value" class="h-4 w-4 rounded-sm" />
                        <span>{{ option.label }}</span>
                      </span>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </label>

              <label class="feed-filter-panel__field">
                <span>时间范围</span>
                <Select :model-value="timeRange" @update:model-value="handleTimeRangeChange">
                  <SelectTrigger aria-label="按时间范围筛选">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="option in timeRangeOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </label>

              <label class="feed-filter-panel__field">
                <span>视频时长</span>
                <Select :model-value="duration" @update:model-value="handleDurationChange">
                  <SelectTrigger aria-label="按视频时长筛选">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="option in durationOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </label>

              <label v-if="!subscriptionId" class="feed-filter-panel__field">
                <span>来源类型</span>
                <Select :model-value="contentType" @update:model-value="handleContentTypeChange">
                  <SelectTrigger aria-label="按来源类型筛选">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="option in contentTypeOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </label>

              <label v-if="settings.showNsfw" class="feed-filter-panel__field">
                <span>内容分级</span>
                <Select :model-value="nsfw" @update:model-value="handleNsfwChange">
                  <SelectTrigger aria-label="按内容分级筛选">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="option in nsfwOptions"
                      :key="option.value"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </label>

              <label v-if="!subscriptionId" class="feed-filter-panel__toggle">
                <span>
                  <strong>特别关注</strong>
                  <small>只显示特别关注频道的视频</small>
                </span>
                <Switch
                  :model-value="special === 'yes'"
                  aria-label="只显示特别关注频道的视频"
                  @update:model-value="handleSpecialChange"
                />
              </label>
            </div>
          </div>
        </PopoverContent>
      </Popover>

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
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import type { TimeRange, Duration, ContentType } from '@/features/video/composables/useFeedFilters'
import { useSites } from '@/features/video/composables/useSites'
import { useUserSettings } from '@/shared/composables/useUserSettings'
import { Button } from '@/shared/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/shared/ui/popover'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/shared/ui/select'
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

const handleSiteChange = (value: unknown) => {
  emit('update:site', value === 'all' ? '' : String(value))
}

const handleTimeRangeChange = (value: unknown) => {
  emit('update:timeRange', String(value) as TimeRange)
}

const handleDurationChange = (value: unknown) => {
  emit('update:duration', String(value) as Duration)
}

const handleContentTypeChange = (value: unknown) => {
  emit('update:contentType', String(value) as ContentType)
}

const handleNsfwChange = (value: unknown) => {
  emit('update:nsfw', String(value))
}

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

const filterDescription = computed(() => (
  activeFilterCount.value > 0
    ? `已启用 ${activeFilterCount.value} 项条件`
    : props.subscriptionId
      ? '按时间和内容范围筛选'
      : '按来源、时间和内容范围筛选'
))

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
  min-height: 2.5rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
}

.feed-toolbar__primary {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
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

.feed-toolbar__filter {
  gap: 0.4rem;
  color: hsl(var(--muted-foreground) / 0.84);
  font-size: 0.75rem;
}

.feed-toolbar__filter.is-active {
  border-color: hsl(var(--foreground) / 0.1);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.82);
}

.feed-toolbar__filter-count {
  display: grid;
  min-width: 1rem;
  height: 1rem;
  place-items: center;
  border-radius: 999px;
  background: hsl(var(--foreground) / 0.08);
  color: hsl(var(--foreground) / 0.72);
  font-size: 0.5625rem;
  line-height: 1;
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

.feed-filter-panel {
  padding: var(--space-4);
}

.feed-filter-panel__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  padding-bottom: var(--space-4);
}

.feed-filter-panel__header > div {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
}

.feed-filter-panel__header strong {
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 650;
}

.feed-filter-panel__header span {
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
}

.feed-filter-panel__fields {
  display: grid;
  gap: var(--space-4);
}

.feed-filter-panel__field {
  display: grid;
  gap: var(--space-2);
}

.feed-filter-panel__field > span {
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.6875rem;
  font-weight: 600;
}

.feed-filter-panel__site-option {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.feed-filter-panel__toggle {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-4);
  border-top: 1px solid var(--app-hairline);
  padding-top: var(--space-4);
}

.feed-filter-panel__toggle > span {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 0.2rem;
}

.feed-filter-panel__toggle strong {
  color: hsl(var(--foreground) / 0.9);
  font-size: 0.75rem;
  font-weight: 600;
}

.feed-filter-panel__toggle small {
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.6875rem;
}
</style>
