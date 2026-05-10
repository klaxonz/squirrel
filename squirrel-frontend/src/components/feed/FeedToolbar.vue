<template>
  <section class="flex flex-col bg-background">
    <div class="flex items-center h-14 px-4 sm:px-6 gap-4 sm:gap-6 border-b border-border/40">
      
      <!-- Left: Navigation Tabs -->
      <nav v-if="showTabs" class="flex items-center h-full space-x-1 overflow-x-auto scrollbar-hide -mb-px shrink-0">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="relative h-full px-3 text-[13px] font-medium whitespace-nowrap transition-colors outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 shrink-0"
          :class="[
            localActiveTab === tab.value 
              ? 'text-foreground' 
              : 'text-muted-foreground hover:text-foreground/80'
          ]"
          @click="localActiveTab = tab.value"
        >
          {{ tab.label }}
          <div 
            v-if="localActiveTab === tab.value"
            class="absolute bottom-0 left-0 right-0 h-[2px] bg-primary rounded-t-full"
          ></div>
        </button>
      </nav>

      <div class="flex-1 min-w-0" />

      <!-- Right: Filter Actions -->
      <div class="flex items-center gap-1.5 sm:gap-2 shrink-0 whitespace-nowrap">
        
        <!-- Site Select -->
        <div class="flex items-center bg-muted/40 hover:bg-muted/60 border border-border/40 rounded-lg px-2.5 h-8 transition-colors shrink-0 whitespace-nowrap">
          <span class="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-wider mr-1.5 select-none hidden sm:inline-block shrink-0">站点</span>
          <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
            <SelectTrigger class="h-auto p-0 border-0 bg-transparent shadow-none hover:bg-transparent focus:ring-0 text-xs font-medium text-foreground gap-1.5 shrink-0 whitespace-nowrap flex-nowrap">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all" class="text-xs">全部站点</SelectItem>
              <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value" class="text-xs">
                {{ opt.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- Sort Select -->
        <div v-if="showSort" class="hidden sm:flex items-center bg-muted/40 hover:bg-muted/60 border border-border/40 rounded-lg px-2.5 h-8 transition-colors shrink-0 whitespace-nowrap">
          <span class="text-[10px] font-semibold text-muted-foreground/60 uppercase tracking-wider mr-1.5 select-none shrink-0">排序</span>
          <Select v-model="localSortBy">
            <SelectTrigger class="h-auto p-0 border-0 bg-transparent shadow-none hover:bg-transparent focus:ring-0 text-xs font-medium text-foreground gap-1.5 shrink-0 whitespace-nowrap flex-nowrap">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
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
          class="relative w-8 h-8 flex items-center justify-center rounded-lg transition-colors border border-transparent outline-none focus-visible:ring-2 focus-visible:ring-primary shrink-0"
          :class="[
            activeFilterCount > 0 
              ? 'bg-primary/10 text-primary border-primary/20' 
              : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground border-border/40'
          ]"
          @click="filterModalOpen = true"
          title="高级筛选"
        >
          <AppIcon name="filter" class="w-4 h-4 shrink-0" />
          <span v-if="activeFilterCount > 0" class="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-primary rounded-full ring-2 ring-background"></span>
        </button>

        <!-- Refresh -->
        <button
          v-if="showRefresh"
          type="button"
          class="w-8 h-8 flex items-center justify-center rounded-lg transition-colors border border-transparent outline-none focus-visible:ring-2 focus-visible:ring-primary text-muted-foreground hover:bg-muted/60 hover:text-foreground border-border/40 shrink-0"
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
  if (props.timeRange !== 'all') c++
  if (props.duration !== 'all') c++
  if (props.contentType !== 'all') c++
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
