<template>
  <aside class="subscription-sidebar">
    <AppSidebarHeader title="订阅频道" :subtitle="`${channels.length} 个频道`">
      <template #actions>
        <Button size="icon-sm" aria-label="添加订阅频道" title="添加订阅频道" @click="$emit('add')">
          <AppIcon name="plus" class="w-4 h-4" />
        </Button>
      </template>
    </AppSidebarHeader>

    <div class="app-pane__controls app-pane__controls--compact">
      <AppSearchInput
        :model-value="search"
        placeholder="搜索订阅..."
        aria-label="搜索订阅"
        @update:model-value="$emit('update:search', $event)"
      />

      <div class="app-pane__filter-row">
        <div ref="siteFilterRef" class="subscription-sidebar__site-filter">
          <Button
            variant="outline"
            size="sm"
            class="app-filter-trigger subscription-sidebar__filter-button"
            :class="{ 'is-selected': site }"
            :aria-expanded="siteDropdownOpen"
            aria-haspopup="listbox"
            @click="$emit('update:siteDropdownOpen', !siteDropdownOpen)"
          >
            <div class="app-filter-trigger__label">
              <AppIcon name="filter" class="h-3.5 w-3.5" :class="site ? 'text-primary' : ''" />
              <span>{{ activeSiteLabel }}</span>
            </div>
            <AppIcon name="chevronRight" class="app-filter-trigger__chevron" :class="{ 'rotate-90': siteDropdownOpen }" />
          </Button>

          <AppFloatingList v-if="siteDropdownOpen">
            <AppListOption
              :selected="!site"
              @click="$emit('update:site', ''); $emit('update:siteDropdownOpen', false)"
            >
              全部来源
            </AppListOption>
            <AppListSeparator />
            <AppListOption
              v-for="opt in siteOptions"
              :key="opt.value"
              :selected="site === opt.value"
              @click="$emit('update:site', opt.value); $emit('update:siteDropdownOpen', false)"
            >
              <SiteIcon :site="opt.value" class="h-4 w-4 rounded-sm" />
              <span class="flex-1 truncate">{{ opt.label }}</span>
            </AppListOption>
          </AppFloatingList>
        </div>

        <Button
          type="button"
          variant="outline"
          size="sm"
          class="app-filter-trigger app-filter-trigger--warning subscription-sidebar__special-filter"
          :class="{ 'is-selected': specialFilter === 'yes' }"
          :aria-pressed="specialFilter === 'yes'"
          @click="$emit('toggle-special-filter')"
        >
          <AppIcon :name="specialFilter === 'yes' ? 'bookmarkCheck' : 'bookmarkPlus'" class="h-3.5 w-3.5" />
          <span>特别关注</span>
        </Button>
      </div>
    </div>

    <div ref="listContainerRef" class="app-pane__list custom-scrollbar">
      <AppSelectableListItem
        v-for="sub in channels"
        :key="sub.id"
        :selected="activeChannelId === sub.id"
        @click="$emit('select-channel', sub.id)"
        @keydown.enter.prevent="$emit('select-channel', sub.id)"
        @keydown.space.prevent="$emit('select-channel', sub.id)"
      >
        <div class="relative shrink-0">
          <SubscriptionAvatar :src="sub.avatar" :name="sub.name" size="md" :class="activeChannelId === sub.id ? 'subscription-sidebar__active-avatar' : ''" />
        </div>

        <div class="flex-1 min-w-0" :class="{'pr-8': sub.is_special_followed}">
          <span class="subscription-sidebar__channel-name" :class="{ 'is-active': activeChannelId === sub.id }">{{ sub.name }}</span>
        </div>

        <Button
          v-if="sub.is_special_followed"
          type="button"
          variant="ghost"
          size="mini-icon"
          class="subscription-sidebar__channel-action is-pinned"
          aria-label="取消特别关注"
          @click.stop="$emit('toggle-special', sub)"
        >
          <AppIcon name="bookmarkCheck" class="h-4 w-4" />
        </Button>

        <Button
          v-else
          type="button"
          variant="ghost"
          size="mini-icon"
          class="subscription-sidebar__channel-action subscription-sidebar__channel-action--ghost"
          aria-label="设为特别关注"
          @click.stop="$emit('toggle-special', sub)"
        >
          <AppIcon name="bookmarkPlus" class="h-4 w-4" />
        </Button>
      </AppSelectableListItem>

      <div v-if="loading" class="subscription-sidebar__loading">
        <AppSkeleton v-for="i in 5" :key="i" height="2.75rem" rounded="var(--radius-md)" shimmer />
      </div>

      <div ref="loadMoreRef" class="subscription-sidebar__load-more">
        <AppSpinner v-if="loadingMore" />
      </div>

      <AppEmptyState
        v-if="finished && !channels.length"
        class="py-10"
        variant="plain"
        icon="inbox"
        title="暂无匹配订阅"
        copy="请尝试更换筛选条件"
      />
    </div>

    <div class="app-pane__footer">
      <Button variant="outline" class="subscription-sidebar__import" @click="$emit('import')">
        <AppIcon name="download" class="mr-2 h-4 w-4 text-muted-foreground" />
        导入订阅
      </Button>
    </div>
  </aside>
</template>

<script setup lang="ts">
/**
 * Subscription channel sidebar for the Subscribed view. Extracted from
 * Subscribed.vue (was a ~130-line template block). Pure presentational +
 * controlled: the parent owns all state (channel list, filters, selection) and
 * passes it down via props; user actions emit back. The load-more sentinel ref
 * is exposed so the parent can attach its IntersectionObserver.
 */
import { ref } from 'vue'
import { usePointerOutside } from '@/shared/composables/usePointerOutside'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppFloatingList from '@/shared/components/layout/AppFloatingList.vue'
import AppListOption from '@/shared/components/layout/AppListOption.vue'
import AppListSeparator from '@/shared/components/layout/AppListSeparator.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import AppSelectableListItem from '@/shared/components/layout/AppSelectableListItem.vue'
import AppSidebarHeader from '@/shared/components/layout/AppSidebarHeader.vue'
import { Button } from '@/shared/ui/button'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

defineProps<{
  channels: SubscriptionListItem[]
  loading: boolean
  loadingMore: boolean
  finished: boolean
  search: string
  site: string
  siteOptions: { value: string; label: string }[]
  activeSiteLabel: string
  siteDropdownOpen: boolean
  specialFilter: 'all' | 'yes'
  activeChannelId: string | number | null
}>()

const emit = defineEmits<{
  'add': []
  'import': []
  'select-channel': [id: string | number]
  'toggle-special': [sub: SubscriptionListItem]
  'toggle-special-filter': []
  'update:search': [value: string]
  'update:site': [value: string]
  'update:siteDropdownOpen': [value: boolean]
}>()

// Local click-outside for the site filter dropdown. The parent owns the open
// state but the dropdown's trigger lives here, so the outside-click handler
// emits the close.
const siteFilterRef = ref<HTMLElement | null>(null)
usePointerOutside(siteFilterRef, () => {
  emit('update:siteDropdownOpen', false)
})

// Expose the list container + load-more sentinel so the parent can attach its
// IntersectionObserver for infinite scroll (the observer needs the actual DOM).
const listContainerRef = ref<HTMLElement | null>(null)
const loadMoreRef = ref<HTMLElement | null>(null)
defineExpose({ listContainer: listContainerRef, loadMore: loadMoreRef })
</script>

<style scoped>
.subscription-sidebar {
  display: flex;
  flex: 0 0 280px;
  width: 280px;
  flex-direction: column;
  border-right: 1px solid hsl(var(--border) / 0.22);
  background: hsl(var(--muted) / 0.1);
}

.subscription-sidebar__channel-name {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.subscription-sidebar__channel-name.is-active {
  font-weight: 600;
}

.subscription-sidebar__site-filter {
  position: relative;
  flex: 1 1 0;
}

.subscription-sidebar__filter-button {
  justify-content: space-between;
  width: 100%;
  padding: 0 0.75rem;
}

.subscription-sidebar__special-filter {
  flex: 1 1 0;
  justify-content: center;
  gap: 0.5rem;
  padding: 0 0.75rem;
}

.subscription-sidebar__active-avatar {
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.28);
}

.subscription-sidebar__channel-action {
  flex: 0 0 auto;
  width: 1.75rem;
  height: 1.75rem;
  color: hsl(var(--warning));
}

.subscription-sidebar__channel-action--ghost {
  position: absolute;
  top: 50%;
  right: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.55);
  opacity: 0;
  transform: translateY(-50%);
}

.app-selectable-list-item:hover .subscription-sidebar__channel-action--ghost,
.app-selectable-list-item:focus-within .subscription-sidebar__channel-action--ghost {
  opacity: 1;
}

.subscription-sidebar__loading {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.5rem;
}

.subscription-sidebar__load-more {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 3rem;
}

.subscription-sidebar__import {
  width: 100%;
  height: 2.25rem;
  justify-content: flex-start;
  border-color: hsl(var(--border) / 0.5);
  border-radius: 0.5rem;
  font-weight: 500;
}

.subscription-sidebar__import:hover {
  background: hsl(var(--background));
}

@media (prefers-reduced-motion: reduce) {
  .app-filter-trigger__chevron {
    transition: none;
  }
}
</style>
