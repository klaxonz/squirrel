<template>
  <div :class="['flex items-center py-3', showTabs ? 'justify-between' : 'justify-end']">
    <TabBar
        v-if="showTabs"
        v-model="localActiveTab"
        :tabs="tabsWithCounts"
        class="custom-tab-bar flex-grow min-w-0"
        @tab-dblclick="$emit('tab-dblclick', $event)"
    />
    <div class="flex items-center flex-shrink-0">
      <NsfwFilter v-if="showNsfw" v-model="localNsfw" class="ml-2" />
      <SiteFilter
          v-if="showSite && !subscriptionId"
          v-model="localSite"
          class="ml-2"
      />
      <SortButton
          v-if="showSort"
          v-model="localSortBy"
          class="ml-2"
      />
      <RefreshButton
        v-if="showRefresh"
        class="ml-2"
        :loading="isRefreshing"
        title="刷新 (R)"
        aria-label="刷新"
        @click="$emit('refresh')"
      />
      <slot />
    </div>
  </div>
</template>

<script setup>
import { watch, ref } from 'vue';
import TabBar from '../TabBar.vue';
import SortButton from '../SortButton.vue';
import NsfwFilter from '../NsfwFilter.vue';
import RefreshButton from '../RefreshButton.vue';
import SiteFilter from '../SiteFilter.vue';

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
});

const emit = defineEmits([
  'update:activeTab',
  'update:nsfw',
  'update:sortBy',
  'update:site',
  'tab-dblclick',
  'refresh'
]);

const localActiveTab = ref(props.activeTab);
const localNsfw = ref(props.nsfw);
const localSortBy = ref(props.sortBy);
const localSite = ref(props.site);

watch(() => props.activeTab, v => localActiveTab.value = v);
watch(() => props.nsfw, v => localNsfw.value = v);
watch(() => props.sortBy, v => localSortBy.value = v);
watch(() => props.site, v => localSite.value = v);

watch(localActiveTab, v => emit('update:activeTab', v));
watch(localNsfw, v => emit('update:nsfw', v));
watch(localSortBy, v => emit('update:sortBy', v));
watch(localSite, v => emit('update:site', v));
</script>

<style scoped>
</style>


