<template>
  <section class="toolbar-minimal">
    <div class="toolbar-inner">
      <div v-if="showTabs || $slots.actions || $slots.default" class="toolbar-primary">
        <div v-if="showTabs" class="toolbar-tabs">
          <button
            v-for="tab in tabsWithCounts"
            :key="tab.value"
            class="tab-item-minimal"
            :class="{ 'is-active': localActiveTab === tab.value }"
            @click="localActiveTab = tab.value"
          >
            <span class="tab-label">{{ tab.label }}</span>
            <span v-if="tab.count > 0" class="tab-count">{{ tab.count }}</span>
          </button>
        </div>

        <div v-if="$slots.actions" class="toolbar-slot-actions">
          <slot name="actions" />
        </div>

        <slot />
      </div>

      <div class="toolbar-actions">
        <NsfwFilter
          v-if="showNsfw"
          v-model="localNsfw"
          class="filter-minimal"
        />
        <SiteFilter
          v-if="showSite && !subscriptionId"
          v-model="localSite"
          class="filter-minimal"
        />
        <SortButton
          v-if="showSort"
          v-model="localSortBy"
          class="filter-minimal"
        />
        <button
          v-if="showRefresh"
          class="refresh-minimal"
          @click="$emit('refresh')"
        >
          <div class="refresh-content">
            <ArrowPathIcon 
              class="refresh-icon" 
              :class="{ 'is-spinning': isRefreshing }" 
            />
            <span class="refresh-label">{{ isRefreshing ? 'SYNCING' : 'REFRESH' }}</span>
          </div>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import NsfwFilter from './NsfwFilter.vue'
import SiteFilter from './SiteFilter.vue'
import SortButton from './SortButton.vue'

const props = defineProps({
  activeTab: { type: String, default: 'all' },
  nsfw: { type: String, default: 'all' },
  sortBy: { type: String, default: 'publish_date' },
  site: { type: String, default: undefined },
  subscriptionId: { type: [String, Number], default: undefined },
  tabsWithCounts: { type: Array, default: () => [] },
  isRefreshing: { type: Boolean, default: false },
  showTabs: { type: Boolean, default: true },
  showNsfw: { type: Boolean, default: true },
  showSite: { type: Boolean, default: true },
  showSort: { type: Boolean, default: true },
  showRefresh: { type: Boolean, default: true },
})

const emit = defineEmits([
  'update:activeTab',
  'update:nsfw',
  'update:sortBy',
  'update:site',
  'tab-dblclick',
  'refresh'
])

const localActiveTab = ref(props.activeTab)
const localNsfw = ref(props.nsfw)
const localSortBy = ref(props.sortBy)
const localSite = ref(props.site)

watch(() => props.activeTab, (value) => localActiveTab.value = value)
watch(() => props.nsfw, (value) => localNsfw.value = value)
watch(() => props.sortBy, (value) => localSortBy.value = value)
watch(() => props.site, (value) => localSite.value = value)

watch(localActiveTab, (value) => emit('update:activeTab', value))
watch(localNsfw, (value) => emit('update:nsfw', value))
watch(localSortBy, (value) => emit('update:sortBy', value))
watch(localSite, (value) => emit('update:site', value))
</script>

<style scoped>
.toolbar-minimal {
  padding: 1rem 2rem;
  background: transparent;
}

.toolbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
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
  color: rgba(255, 255, 255, 0.2);
  cursor: pointer;
  transition: all 0.3s;
  padding: 0.5rem 0;
}

.tab-item-minimal:hover {
  color: rgba(255, 255, 255, 0.6);
}

.tab-item-minimal.is-active {
  color: #fff;
  border-bottom: 1px solid #ff4d00;
}

.tab-label {
  font-size: 0.7rem;
  font-weight: 500;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.tab-count {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  opacity: 0.5;
}

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}

.toolbar-slot-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.refresh-minimal {
  background: transparent;
  border: none;
  padding: 0;
  cursor: pointer;
  transition: all 0.3s;
}

.refresh-content {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-family: 'Courier New', Courier, monospace;
  text-transform: uppercase;
  font-size: 0.6rem;
  letter-spacing: 0.1em;
  color: rgba(255, 255, 255, 0.3);
}

.refresh-minimal:hover .refresh-content {
  color: #fff;
}

.refresh-label {
  font-weight: 600;
  color: #ff4d00;
}

.refresh-icon {
  width: 0.8rem;
  height: 0.8rem;
  opacity: 0.5;
  transition: all 0.3s;
}

.refresh-minimal:hover .refresh-icon {
  opacity: 1;
}

.is-spinning {
  animation: spin 1s linear infinite;
  opacity: 1;
  color: #ff4d00;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
