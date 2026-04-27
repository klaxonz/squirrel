<template>
  <section class="feed-toolbar">
    <div class="toolbar-container">
      <!-- Left: Navigation Tabs -->
      <div v-if="showTabs" class="nav-group">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          class="nav-tab"
          :class="{ 'is-active': localActiveTab === tab.value }"
          @click="localActiveTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>

      <div class="flex-1" />

      <!-- Right: Filter Actions -->
      <div class="filter-group">
        <!-- Site Select -->
        <div class="property-pill">
          <span class="property-label">站点</span>
          <Select :model-value="site || 'all'" @update:model-value="handleSiteChange">
            <SelectTrigger class="property-trigger">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部站点</SelectItem>
              <SelectItem v-for="opt in siteOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- Sort Select -->
        <div v-if="showSort" class="property-pill">
          <span class="property-label">排序</span>
          <Select v-model="localSortBy">
            <SelectTrigger class="property-trigger">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem v-for="opt in sortOptions" :key="opt.value" :value="opt.value">
                {{ opt.label }}
              </SelectItem>
            </SelectContent>
          </Select>
        </div>

        <!-- Advanced Filter -->
        <button
          v-if="showFilter"
          type="button"
          class="icon-action-btn"
          :class="{ 'is-active': activeFilterCount > 0 }"
          @click="filterModalOpen = true"
        >
          <AppIcon name="filter" class="w-3.5 h-3.5" />
          <span v-if="activeFilterCount > 0" class="active-dot" />
        </button>
        
        <div class="w-px h-3 bg-border/40 mx-1.5" />

        <!-- Refresh -->
        <button
          v-if="showRefresh"
          type="button"
          class="icon-action-btn"
          @click="$emit('refresh')"
        >
          <AppIcon
            name="refresh"
            class="w-3.5 h-3.5"
            :class="{ 'is-spinning': isRefreshing }"
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

<style scoped>
.feed-toolbar {
  display: flex;
  flex-direction: column;
  background: hsl(var(--background));
}

.toolbar-container {
  display: flex;
  align-items: center;
  height: 3.5rem;
  padding: 0 1.5rem;
  gap: 1.25rem;
}

.nav-group {
  display: flex;
  align-items: center;
  gap: 1.75rem;
  height: 100%;
}

.nav-tab {
  height: 100%;
  display: flex;
  align-items: center;
  font-size: 13px;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.4);
  transition: all 0.2s;
  position: relative;
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
  letter-spacing: -0.01em;
}

.nav-tab:hover { color: hsl(var(--foreground) / 0.8); }
.nav-tab.is-active { color: hsl(var(--foreground)); }
.nav-tab.is-active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: -2px;
  right: -2px;
  height: 2px;
  background: hsl(var(--foreground));
  border-radius: 2px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.property-pill {
  display: flex;
  align-items: center;
  gap: 0.375rem;
  height: 2.125rem;
  padding: 0 0.5rem 0 0.875rem;
  background: hsl(var(--accent) / 0.3);
  border-radius: var(--radius-md);
  transition: all 0.2s;
}

.property-pill:hover { background: hsl(var(--accent) / 0.6); }

.property-label {
  font-size: 10px;
  font-weight: 800;
  color: hsl(var(--muted-foreground) / 0.3);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  user-select: none;
}

.property-trigger {
  background: none !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
  height: auto !important;
  font-size: 12px !important;
  font-weight: 700 !important;
  color: hsl(var(--foreground) / 0.9) !important;
  width: auto !important;
  min-width: 40px;
  gap: 0.25rem;
}

.icon-action-btn {
  width: 2.125rem;
  height: 2.125rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  color: hsl(var(--muted-foreground) / 0.6);
  transition: all 0.2s;
  cursor: pointer;
  background: none;
  border: none;
  position: relative;
}

.icon-action-btn:hover {
  background: hsl(var(--accent) / 0.6);
  color: hsl(var(--foreground));
}

.icon-action-btn.is-active {
  color: hsl(var(--foreground));
  background: hsl(var(--foreground) / 0.05);
}

.active-dot {
  position: absolute;
  top: 6px;
  right: 6px;
  width: 7px;
  height: 7px;
  background: hsl(var(--primary));
  border-radius: 50%;
  border: 2px solid hsl(var(--background));
}

.is-spinning { animation: spin 1s linear infinite; }
@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
</style>
