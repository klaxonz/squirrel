<template>
  <section class="feed-toolbar-shell">
    <div class="feed-toolbar__inner" :class="{ 'feed-toolbar__inner--compact': !showTabs }">
      <div v-if="showTabs" class="feed-toolbar__tabs">
        <TabBar
          v-if="showTabs"
          v-model="localActiveTab"
          :tabs="tabsWithCounts"
          class="w-full"
          @tab-dblclick="$emit('tab-dblclick', $event)"
        />
      </div>

      <div class="feed-toolbar__actions">
        <NsfwFilter
          v-if="showNsfw"
          v-model="localNsfw"
          :open="openSelectKey === 'nsfw'"
          @update:open="(value) => handleOpenChange('nsfw', value)"
        />
        <SiteFilter
          v-if="showSite && !subscriptionId"
          v-model="localSite"
          :open="openSelectKey === 'site'"
          @update:open="(value) => handleOpenChange('site', value)"
        />
        <SortButton
          v-if="showSort"
          v-model="localSortBy"
          :open="openSelectKey === 'sort'"
          @update:open="(value) => handleOpenChange('sort', value)"
        />
        <RefreshButton
          v-if="showRefresh"
          :loading="isRefreshing"
          title="刷新 (R)"
          aria-label="刷新"
          @click="$emit('refresh')"
        />
        <slot />
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, watch } from 'vue'
import NsfwFilter from './NsfwFilter.vue'
import RefreshButton from './RefreshButton.vue'
import SiteFilter from './SiteFilter.vue'
import SortButton from './SortButton.vue'
import TabBar from './TabBar.vue'

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
const openSelectKey = ref('')

watch(() => props.activeTab, (value) => localActiveTab.value = value)
watch(() => props.nsfw, (value) => localNsfw.value = value)
watch(() => props.sortBy, (value) => localSortBy.value = value)
watch(() => props.site, (value) => localSite.value = value)

watch(localActiveTab, (value) => emit('update:activeTab', value))
watch(localNsfw, (value) => emit('update:nsfw', value))
watch(localSortBy, (value) => emit('update:sortBy', value))
watch(localSite, (value) => emit('update:site', value))

const handleOpenChange = (key, value) => {
  openSelectKey.value = value ? key : (openSelectKey.value === key ? '' : openSelectKey.value)
}
</script>

<style scoped>
.feed-toolbar-shell {
  padding-block: 0.25rem 0.75rem;
}

.feed-toolbar__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.375rem;
  border: none;
  border-radius: calc(var(--radius-xl) + 2px);
  background: transparent;
  box-shadow: none;
}

.feed-toolbar__inner--compact {
  justify-content: flex-end;
}

.feed-toolbar__tabs {
  flex: 1 1 auto;
  min-width: 0;
  overflow: visible;
}

.feed-toolbar__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.45rem;
  flex-shrink: 0;
  flex-wrap: wrap;
}

@media (max-width: 1024px) {
  .feed-toolbar__inner {
    flex-direction: column;
    align-items: stretch;
  }

  .feed-toolbar__actions {
    justify-content: flex-start;
  }
}

@media (max-width: 640px) {
  .feed-toolbar-shell {
    padding-block: 0.2rem 0.65rem;
  }

  .feed-toolbar__inner {
    gap: 0.625rem;
    padding: 0.35rem;
    border-radius: 0.875rem;
  }

  .feed-toolbar__actions {
    gap: 0.35rem;
  }
}
</style>
