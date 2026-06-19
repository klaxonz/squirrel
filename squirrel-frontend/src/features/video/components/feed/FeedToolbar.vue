<template>
  <section class="flex w-full items-center justify-between gap-3 bg-transparent relative z-10">
    <div class="flex items-center gap-3 min-w-0">
      <nav v-if="showTabs" class="relative shrink-0 min-w-0">
        <div
          ref="tabsScroll"
          class="flex items-center h-full gap-0.5 overflow-x-auto scrollbar-hide"
          @scroll="updateScrollState"
        >
          <button
            v-for="tab in tabs"
            :key="tab.value"
            class="flex items-center text-[13px] font-semibold whitespace-nowrap transition-colors outline-none focus-visible:ring-0 shrink-0"
            @click="localActiveTab = tab.value"
          >
            <span class="relative inline-flex items-center px-3.5 py-1.5 rounded-full transition-all duration-200"
                  :class="localActiveTab === tab.value ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'">
              {{ tab.label }}
            </span>
          </button>
        </div>
        <!-- Edge fade hints: only when that direction is scrollable -->
        <div v-if="canScrollLeft" class="pointer-events-none absolute inset-y-0 left-0 w-4 bg-gradient-to-r from-background to-transparent"></div>
        <div v-if="canScrollRight" class="pointer-events-none absolute inset-y-0 right-0 w-4 bg-gradient-to-l from-background to-transparent"></div>
      </nav>
    </div>

    <!-- Right: Filter Actions -->
    <div class="flex items-center gap-1 shrink-0 whitespace-nowrap">
      <!-- Special-follow chip (active state) -->
      <button
        v-if="special === 'yes'"
        type="button"
        class="inline-flex h-8 shrink-0 items-center gap-1.5 rounded-full border border-amber-400/40 bg-amber-400/10 px-3 text-xs font-semibold text-amber-600 transition-colors hover:bg-amber-400/15"
        title="清除特别关注过滤"
        @click="emit('update:special', 'all')"
      >
        <AppIcon name="star" class="h-3.5 w-3.5 fill-current" />
        特别关注
        <AppIcon name="close" class="h-3 w-3" />
      </button>

      <!-- Site Select -->
      <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
        <SelectTrigger class="h-8 w-auto min-w-0 shrink-0 flex-nowrap whitespace-nowrap border-0 bg-muted/40 px-3 py-0 text-[13px] font-semibold text-muted-foreground shadow-none hover:bg-muted/70 hover:text-foreground focus:ring-0 rounded-full transition-colors">
          <SelectValue />
        </SelectTrigger>
        <SelectContent class="min-w-44 border-border/10 bg-background/70 backdrop-blur-2xl shadow-2xl rounded-md">
          <SelectItem value="all" class="text-xs">全部站点</SelectItem>
          <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">
            {{ opt.label }}
          </SelectItem>
        </SelectContent>
      </Select>

      <!-- Sort Select -->
      <div v-if="showSort" class="hidden sm:block shrink-0">
        <Select v-model="localSortBy">
          <SelectTrigger class="h-8 w-auto min-w-0 flex-nowrap whitespace-nowrap border-0 bg-muted/40 px-3 py-0 text-[13px] font-semibold text-muted-foreground shadow-none hover:bg-muted/70 hover:text-foreground focus:ring-0 rounded-full transition-colors">
            <SelectValue />
          </SelectTrigger>
          <SelectContent class="min-w-36 border-border/10 bg-background/70 backdrop-blur-2xl shadow-2xl rounded-md">
            <SelectItem v-for="opt in sortOptions" :key="opt.value" :value="opt.value" class="text-xs">
              {{ opt.label }}
            </SelectItem>
          </SelectContent>
        </Select>
      </div>

      <!-- Advanced Filter -->
      <button
        v-if="showFilter"
        type="button"
        class="relative flex size-8 shrink-0 items-center justify-center rounded-full transition-colors outline-none focus-visible:ring-0 border-0"
        :class="[
          activeFilterCount > 0
            ? 'bg-primary/10 text-primary hover:bg-primary/20'
            : 'bg-muted/40 text-muted-foreground hover:bg-muted/70 hover:text-foreground'
        ]"
        @click="filterModalOpen = true"
        :title="activeFilterCount > 0 ? '筛选已启用' : '筛选'"
        :aria-label="activeFilterCount > 0 ? '筛选已启用' : '筛选'"
      >
        <AppIcon name="filter" class="size-4 shrink-0" />
      </button>

      <!-- View Mode Toggle -->
      <div class="hidden sm:flex p-0.5 shrink-0 items-center gap-0.5 bg-muted/40 rounded-full">
        <button
          class="flex items-center justify-center size-7 rounded-full transition-colors"
          :class="uiStore.viewMode === 'grid' ? 'text-foreground bg-background shadow-sm' : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'"
          @click="uiStore.setViewMode('grid')"
          title="网格视图"
        >
          <AppIcon name="layoutGrid" class="w-4 h-4" />
        </button>
        <button
          class="flex items-center justify-center size-7 rounded-full transition-colors"
          :class="uiStore.viewMode === 'list' ? 'text-foreground bg-background shadow-sm' : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground'"
          @click="uiStore.setViewMode('list')"
          title="列表视图"
        >
          <AppIcon name="list" class="w-4 h-4" />
        </button>
      </div>

      <!-- Refresh -->
      <button
        v-if="showRefresh"
        type="button"
        class="flex size-8 shrink-0 items-center justify-center rounded-full border-0 text-muted-foreground transition-colors outline-none bg-muted/40 hover:bg-muted/70 hover:text-foreground focus-visible:ring-0"
        @click="$emit('refresh')"
        title="刷新内容"
      >
        <AppIcon
          name="refresh"
          class="w-4 h-4 shrink-0"
          :class="{ 'animate-spin': isRefreshing }"
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
