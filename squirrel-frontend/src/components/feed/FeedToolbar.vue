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
  gap: var(--space-4);
  padding: var(--space-2) var(--space-4);
}

.toolbar-primary {
  display: flex;
  align-items: center;
  gap: var(--space-5);
  min-width: 0;
  flex: 1 1 auto;
}

.toolbar-tabs {
  display: flex;
  gap: var(--space-5);
}

.tab-item-minimal {
  background: transparent;
  border: none;
  display: flex;
  align-items: center;
  gap: var(--space-1);
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition:
    color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default);
  padding: var(--space-2) 0;
  border-bottom: 2px solid transparent;
}

.tab-item-minimal:hover {
  color: hsl(var(--foreground));
}

.tab-item-minimal.is-active {
  color: hsl(var(--foreground));
  border-bottom-color: hsl(var(--primary));
}

.tab-label {
  font-size: var(--font-size-xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.toolbar-slot-actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.filter-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  background: transparent;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: var(--radius-md);
  padding: var(--space-1) var(--space-3);
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
  position: relative;
}

.filter-toggle-btn:hover {
  border-color: hsl(var(--border));
  color: hsl(var(--foreground));
  background: hsl(var(--secondary) / 0.4);
}

.filter-toggle-btn.is-active {
  background: hsl(var(--primary) / 0.1);
  border-color: hsl(var(--primary) / 0.5);
  color: hsl(var(--foreground));
}

.filter-toggle-icon {
  width: 14px;
  height: 14px;
}

.filter-toggle-label {
  font-family: var(--font-mono);
  font-size: var(--font-size-2xs);
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.filter-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 var(--space-1);
  border-radius: var(--radius-full);
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
}

.refresh-minimal {
  background: transparent;
  border: none;
  padding: var(--space-1);
  cursor: pointer;
  transition:
    opacity var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
  display: flex;
  align-items: center;
  border-radius: var(--radius-sm);
}

.refresh-minimal:hover {
  background: hsl(var(--secondary) / 0.5);
}

.refresh-icon {
  width: 16px;
  height: 16px;
  opacity: 0.6;
  transition:
    opacity var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default),
    transform var(--duration-fast) var(--ease-default);
  color: hsl(var(--muted-foreground));
}

.refresh-minimal:hover .refresh-icon {
  opacity: 1;
  color: hsl(var(--primary));
}

.is-spinning {
  animation: spin 1s linear infinite;
  opacity: 1;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 640px) {
  .toolbar-inner {
    padding: var(--space-2);
    gap: var(--space-2);
  }

  .toolbar-tabs {
    gap: var(--space-3);
  }

  .tab-label {
    font-size: var(--font-size-2xs);
  }

  .filter-toggle-label {
    display: none;
  }
}
</style>
