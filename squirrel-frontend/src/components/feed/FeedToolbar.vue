<template>
  <section class="toolbar-minimal">
    <div class="toolbar-inner">
      <div v-if="showTabs || $slots.actions || $slots.default" class="toolbar-primary">
        <div v-if="showTabs" class="toolbar-tabs">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            class="tab-item-minimal"
            :class="{ 'is-active': localActiveTab === tab.value }"
            @click="localActiveTab = tab.value"
          >
            <span class="tab-label">{{ tab.label }}</span>
          </button>
        </div>

        <div v-if="$slots.actions" class="toolbar-slot-actions">
          <slot name="actions" />
        </div>

        <slot />
      </div>

      <div class="toolbar-actions">
        <button
          v-if="showFilter"
          class="filter-toggle-btn"
          :class="{ 'is-active': filterModalOpen || hasActiveFilters }"
          aria-label="筛选"
          @click="filterModalOpen = true"
        >
          <FunnelIcon class="filter-toggle-icon" />
          <span class="filter-toggle-label">筛选</span>
          <span v-if="activeFilterCount > 0" class="filter-badge">{{ activeFilterCount }}</span>
        </button>
        <button
          v-if="showRefresh"
          class="refresh-minimal"
          :aria-label="isRefreshing ? 'Syncing' : 'Refresh'"
          @click="$emit('refresh')"
        >
          <ArrowPathIcon
            class="refresh-icon"
            :class="{ 'is-spinning': isRefreshing }"
          />
        </button>
      </div>
    </div>

    <FilterModal
      v-model="filterModalOpen"
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
      @update:site="(v) => { emit('update:site', v) }"
      @update:sort-by="(v) => { localSortBy = v }"
    />
  </section>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import {
  ArrowPathIcon,
  FunnelIcon,
} from '@heroicons/vue/24/outline'
import FilterModal from './FilterModal.vue'
import type { TimeRange, Duration, ContentType } from '@/composables/useFeedFilters'
import type { VideoTab } from '@/constants/videos'

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
  siteLabel?: string
  /** Controls which filter sections FilterModal shows: 'video' (full) or 'subscription' (minimal) */
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
  'tab-dblclick',
  'refresh',
])

const localActiveTab = ref(props.activeTab)
const localSortBy = ref(props.sortBy)
const filterModalOpen = ref(false)

const hasActiveFilters = computed(() => {
  return (
    (props.site != null && props.site !== '')
    || (props.nsfw != null && props.nsfw !== 'all')
    || (props.timeRange != null && props.timeRange !== 'all')
    || (props.duration != null && props.duration !== 'all')
    || (props.contentType != null && props.contentType !== 'all')
  )
})

const activeFilterCount = computed(() => {
  let c = 0
  if (props.timeRange !== 'all') c++
  if (props.duration !== 'all') c++
  if (props.contentType !== 'all') c++
  if (props.nsfw !== 'all') c++
  if (props.site) c++
  return c
})

// Sync props → local
watch(() => props.activeTab, (v) => { localActiveTab.value = v })
watch(() => props.sortBy, (v) => { localSortBy.value = v })
// Sync local → emit
watch(localActiveTab, (v) => emit('update:activeTab', v))
watch(localSortBy, (v) => emit('update:sortBy', v))
</script>

<style scoped>
.toolbar-minimal {
  display: flex;
  flex-direction: column;
}

.toolbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.5rem 1rem;
}

.toolbar-primary {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  min-width: 0;
  flex: 1 1 auto;
}

.toolbar-tabs {
  display: flex;
  gap: 1.5rem;
}

.tab-item-minimal {
  background: transparent;
  border: none;
  display: flex;
  align-items: center;
  gap: 0.4rem;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition: all 0.2s;
  padding: 0.5rem 0;
}

.tab-item-minimal:hover {
  color: hsl(var(--foreground) / 0.6);
}

.tab-item-minimal.is-active {
  color: hsl(var(--foreground));
  border-bottom: 1px solid hsl(var(--primary));
}

.tab-label {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.toolbar-slot-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.filter-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  background: transparent;
  border: 1px solid hsl(var(--border) / 0.4);
  border-radius: var(--radius-md);
  padding: 0.3rem 0.625rem;
  color: hsl(var(--muted-foreground) / 0.7);
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.filter-toggle-btn:hover {
  border-color: hsl(var(--border));
  color: hsl(var(--foreground));
  background: hsl(var(--secondary) / 0.3);
}

.filter-toggle-btn.is-active {
  background: hsl(var(--primary) / 0.08);
  border-color: hsl(var(--primary) / 0.4);
  color: hsl(var(--foreground));
}

.filter-toggle-icon {
  width: 0.875rem;
  height: 0.875rem;
}

.filter-toggle-label {
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.filter-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 1rem;
  height: 1rem;
  padding: 0 0.2rem;
  border-radius: 9999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.refresh-minimal {
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.refresh-icon {
  width: 1rem;
  height: 1rem;
  opacity: 0.5;
  transition: all 0.2s;
  color: hsl(var(--muted-foreground));
}

.refresh-minimal:hover .refresh-icon {
  opacity: 1;
  color: hsl(var(--primary));
}

.is-spinning {
  animation: spin 1s linear infinite;
  opacity: 1;
  color: hsl(var.primary);
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
