<template>
  <section class="flex flex-col bg-background">
    <div class="flex items-center h-14 px-4 sm:px-6 gap-4 sm:gap-6">
      
      <!-- Left: Navigation Tabs -->
      <nav v-if="showTabs" class="flex items-center h-full space-x-1 overflow-x-auto scrollbar-hide shrink-0">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="h-full px-3 flex items-center text-[13px] font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 shrink-0"
          :class="[
            localActiveTab === tab.value 
              ? 'text-foreground' 
              : 'text-muted-foreground hover:text-foreground/80'
          ]"
          @click="localActiveTab = tab.value"
        >
          <span class="relative inline-flex items-center leading-6">
            {{ tab.label }}
            <span
              v-if="localActiveTab === tab.value"
              class="absolute -bottom-1 left-0 right-0 h-[2px] bg-primary rounded-full"
            />
          </span>
        </button>
      </nav>

      <div class="flex-1 min-w-0" />

      <!-- Right: Filter Actions -->
      <div class="flex items-center gap-1.5 sm:gap-2 shrink-0 whitespace-nowrap">
        
        <!-- Site Select -->
        <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
          <SelectTrigger class="h-8 w-auto min-w-0 shrink-0 flex-nowrap whitespace-nowrap border-border/40 bg-muted/40 px-2.5 py-0 text-xs font-medium text-foreground shadow-none hover:bg-muted/60 focus:ring-primary/20">
            <span class="hidden shrink-0 select-none text-[10px] font-semibold uppercase text-muted-foreground/60 sm:inline-block">站点</span>
            <SelectValue />
          </SelectTrigger>
          <SelectContent class="min-w-44">
            <SelectItem value="all" class="text-xs">全部站点</SelectItem>
            <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">
              {{ opt.label }}
            </SelectItem>
          </SelectContent>
        </Select>

        <!-- Sort Select -->
        <div v-if="showSort" class="hidden sm:block shrink-0">
          <Select v-model="localSortBy">
            <SelectTrigger class="h-8 w-auto min-w-0 flex-nowrap whitespace-nowrap border-border/40 bg-muted/40 px-2.5 py-0 text-xs font-medium text-foreground shadow-none hover:bg-muted/60 focus:ring-primary/20">
              <span class="shrink-0 select-none text-[10px] font-semibold uppercase text-muted-foreground/60">排序</span>
              <SelectValue />
            </SelectTrigger>
            <SelectContent class="min-w-36">
              <SelectItem v-for="opt in sortOptions" :key="opt.value" :value="opt.value" class="text-xs">
                {{ opt.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div class="w-px h-4 bg-border/50 mx-1 hidden sm:block shrink-0" />

        <!-- Advanced Filter -->
        <button
          v-if="showFilter"
          type="button"
          class="relative flex size-8 shrink-0 items-center justify-center rounded-lg border transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary"
          :class="[
            activeFilterCount > 0 
              ? 'bg-primary/10 text-primary border-primary/20' 
              : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground border-border/40'
          ]"
          @click="filterModalOpen = true"
          :title="activeFilterCount > 0 ? '筛选已启用' : '筛选'"
          :aria-label="activeFilterCount > 0 ? '筛选已启用' : '筛选'"
        >
          <AppIcon name="filter" class="size-4 shrink-0" />
        </button>

        <!-- Refresh -->
        <button
          v-if="showRefresh"
          type="button"
          class="flex size-8 shrink-0 items-center justify-center rounded-lg border border-border/40 text-muted-foreground transition-colors outline-none hover:bg-muted/60 hover:text-foreground focus-visible:ring-2 focus-visible:ring-primary"
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
import { ref, computed, watch, onMounted } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import FilterModal from './FilterModal.vue'
import type { TimeRange, Duration, ContentType } from '@/composables/useFeedFilters'
import type { VideoTab } from '@/constants/videos'
import { useSites } from '@/composables/useSites'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

const props = withDefaults(defineProps<{
  activeTab?: string, nsfw?: string, sortBy?: string, site?: string, subscriptionId?: string | number,
  tabs?: VideoTab[], isRefreshing?: boolean, showTabs?: boolean, showSort?: boolean, showRefresh?: boolean,
  showFilter?: boolean, timeRange?: TimeRange, duration?: Duration, contentType?: ContentType,
  siteLabel?: string, filterScope?: 'video' | 'subscription'
}>(), {
  activeTab: 'all', nsfw: 'all', sortBy: 'publish_date', tabs: () => [], isRefreshing: false,
  showTabs: true, showSort: true, showRefresh: true, showFilter: true,
  timeRange: 'all', duration: 'all', contentType: 'all', filterScope: 'video',
})

const emit = defineEmits([
  'update:activeTab', 'update:nsfw', 'update:sortBy', 'update:site',
  'update:timeRange', 'update:duration', 'update:contentType', 'refresh',
])

const { options: siteOptions, fetchSites } = useSites()
const localActiveTab = ref(props.activeTab)
const localSortBy = ref(props.sortBy)
const filterModalOpen = ref(false)

const handleSiteChange = (val: any) => emit('update:site', val === 'all' ? '' : val)

const activeFilterCount = computed(() => {
  let c = 0
  if (localSortBy.value !== 'publish_date') c++
  if (props.timeRange !== 'all') c++
  if (props.duration !== 'all') c++
  if (!props.subscriptionId && props.contentType !== 'all') c++
  if (props.nsfw !== 'all') c++
  if (props.site) c++
  return c
})

watch(() => props.activeTab, (v) => { localActiveTab.value = v })
watch(() => props.sortBy, (v) => { localSortBy.value = v })
watch(localActiveTab, (v) => emit('update:activeTab', v))
watch(localSortBy, (v) => emit('update:sortBy', v))

onMounted(() => { fetchSites() })

const sortOptions = [
  { value: 'publish_date', label: '上传日期' },
  { value: 'created_at', label: '抓取日期' },
]
</script>
