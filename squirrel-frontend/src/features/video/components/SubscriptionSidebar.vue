<template>
  <aside class="subscription-sidebar">
    <div class="subscription-sidebar__header">
      <div class="subscription-sidebar__title-block">
        <h1 class="app-h3 truncate">订阅频道</h1>
        <p class="subscription-sidebar__count">{{ channels.length }} 个频道</p>
      </div>
      <Button size="icon-sm" @click="$emit('add')">
        <AppIcon name="plus" class="w-4 h-4" />
      </Button>
    </div>

    <div class="subscription-sidebar__filters">
      <div class="subscription-sidebar__search">
        <AppIcon name="search" class="subscription-sidebar__search-icon" />
        <input
          :value="search"
          @input="$emit('update:search', ($event.target as HTMLInputElement).value)"
          type="text"
          placeholder="搜索订阅..."
          aria-label="搜索订阅"
          class="subscription-sidebar__search-input"
        />
      </div>

      <div class="subscription-sidebar__filter-row">
        <div ref="siteFilterRef" class="subscription-sidebar__site-filter">
          <button
            class="subscription-sidebar__filter-button"
            :class="{ 'is-selected': site }"
            :aria-expanded="siteDropdownOpen"
            aria-haspopup="listbox"
            @click="$emit('update:siteDropdownOpen', !siteDropdownOpen)"
          >
            <div class="subscription-sidebar__filter-label">
              <AppIcon name="filter" class="h-3.5 w-3.5" :class="site ? 'text-primary' : ''" />
              <span>{{ activeSiteLabel }}</span>
            </div>
            <AppIcon name="chevronRight" class="subscription-sidebar__filter-chevron" :class="{ 'rotate-90': siteDropdownOpen }" />
          </button>

          <div v-if="siteDropdownOpen" class="subscription-sidebar__site-menu">
            <div class="subscription-sidebar__site-list custom-scrollbar">
              <button
                @click="$emit('update:site', ''); $emit('update:siteDropdownOpen', false)"
                class="subscription-sidebar__site-option"
                :class="{ 'is-selected': !site }"
              >全部来源</button>
              <div class="subscription-sidebar__separator"></div>
              <button
                v-for="opt in siteOptions"
                :key="opt.value"
                @click="$emit('update:site', opt.value); $emit('update:siteDropdownOpen', false)"
                class="subscription-sidebar__site-option"
                :class="{ 'is-selected': site === opt.value }"
              >
                <SiteIcon :site="opt.value" class="h-4 w-4 rounded-sm" />
                <span class="flex-1 truncate">{{ opt.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="subscription-sidebar__special-filter"
          :class="{ 'is-selected': specialFilter === 'yes' }"
          :aria-pressed="specialFilter === 'yes'"
          @click="$emit('toggle-special-filter')"
        >
          <AppIcon :name="specialFilter === 'yes' ? 'bookmarkCheck' : 'bookmarkPlus'" class="h-3.5 w-3.5" />
          <span>特别关注</span>
        </button>
      </div>
    </div>

    <div ref="listContainerRef" class="subscription-sidebar__list custom-scrollbar">
      <div
        v-for="sub in channels"
        :key="sub.id"
        role="button"
        tabindex="0"
        @click="$emit('select-channel', sub.id)"
        @keydown.enter.prevent="$emit('select-channel', sub.id)"
        @keydown.space.prevent="$emit('select-channel', sub.id)"
        class="subscription-sidebar__channel"
        :class="{ 'is-active': activeChannelId === sub.id }"
      >
        <div class="relative shrink-0">
          <SubscriptionAvatar :src="sub.avatar" :name="sub.name" size="md" :class="activeChannelId === sub.id ? 'subscription-sidebar__active-avatar' : ''" />
        </div>

        <div class="flex-1 min-w-0" :class="{'pr-8': sub.is_special_followed}">
          <span class="block truncate" :class="activeChannelId === sub.id ? 'font-bold' : 'font-medium'">{{ sub.name }}</span>
        </div>

        <button
          v-if="sub.is_special_followed"
          type="button"
          class="subscription-sidebar__channel-action is-pinned"
          aria-label="取消特别关注"
          @click.stop="$emit('toggle-special', sub)"
        >
          <AppIcon name="bookmarkCheck" class="h-4 w-4" />
        </button>

        <button
          v-else
          type="button"
          class="subscription-sidebar__channel-action subscription-sidebar__channel-action--ghost"
          aria-label="设为特别关注"
          @click.stop="$emit('toggle-special', sub)"
        >
          <AppIcon name="bookmarkPlus" class="h-4 w-4" />
        </button>
      </div>

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

    <div class="subscription-sidebar__footer">
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

.subscription-sidebar__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex: 0 0 auto;
  height: 3.5rem;
  padding: 0 1rem;
  border-bottom: 1px solid hsl(var(--border) / 0.22);
  background: hsl(var(--background) / 0.52);
}

.subscription-sidebar__title-block {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
}

.subscription-sidebar__count {
  margin-top: 0.125rem;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.75rem;
  font-weight: 500;
}

.subscription-sidebar__filters {
  z-index: 10;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0.75rem;
  border-bottom: 1px solid hsl(var(--border) / 0.14);
  background: hsl(var(--background) / 0.2);
}

.subscription-sidebar__search,
.subscription-sidebar__site-filter {
  position: relative;
}

.subscription-sidebar__search-icon {
  position: absolute;
  top: 50%;
  left: 0.75rem;
  width: 1rem;
  height: 1rem;
  color: hsl(var(--muted-foreground) / 0.62);
  transform: translateY(-50%);
  transition: color 0.16s ease;
  pointer-events: none;
}

.subscription-sidebar__search:focus-within .subscription-sidebar__search-icon {
  color: hsl(var(--primary));
}

.subscription-sidebar__search-input,
.subscription-sidebar__filter-button,
.subscription-sidebar__special-filter {
  min-height: 2rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  outline: none;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.subscription-sidebar__search-input {
  width: 100%;
  padding: 0 0.75rem 0 2.25rem;
}

.subscription-sidebar__search-input::placeholder {
  color: hsl(var(--muted-foreground) / 0.55);
}

.subscription-sidebar__search-input:hover,
.subscription-sidebar__filter-button:hover,
.subscription-sidebar__special-filter:hover {
  background: hsl(var(--muted) / 0.6);
  color: hsl(var(--foreground));
}

.subscription-sidebar__search-input:focus {
  border-color: hsl(var(--primary) / 0.32);
  background: hsl(var(--background));
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.14);
}

.subscription-sidebar__filter-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.subscription-sidebar__site-filter {
  flex: 1 1 0;
}

.subscription-sidebar__filter-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0 0.75rem;
}

.subscription-sidebar__filter-button.is-selected,
.subscription-sidebar__special-filter.is-selected {
  border-color: hsl(var(--primary) / 0.22);
  background: hsl(var(--primary) / 0.07);
  color: hsl(var(--foreground));
}

.subscription-sidebar__filter-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.subscription-sidebar__filter-chevron {
  width: 0.875rem;
  height: 0.875rem;
  transition: transform 0.16s ease;
}

.subscription-sidebar__site-menu {
  position: absolute;
  top: 100%;
  right: 0;
  left: 0;
  z-index: var(--z-dropdown, 50);
  margin-top: 0.375rem;
  padding: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.5);
  border-radius: 0.5rem;
  background: hsl(var(--popover));
}

.subscription-sidebar__site-list {
  max-height: 17.5rem;
  padding-right: 0.25rem;
  overflow-y: auto;
}

.subscription-sidebar__site-option {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  min-height: 2rem;
  padding: 0 0.75rem;
  border-radius: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  text-align: left;
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}

.subscription-sidebar__site-option:hover,
.subscription-sidebar__site-option.is-selected {
  background: hsl(var(--accent) / 0.55);
  color: hsl(var(--foreground));
}

.subscription-sidebar__separator {
  height: 1px;
  margin: 0.25rem 0;
  background: hsl(var(--border) / 0.5);
}

.subscription-sidebar__special-filter {
  display: flex;
  flex: 1 1 0;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0 0.75rem;
}

.subscription-sidebar__special-filter.is-selected {
  border-color: hsl(var(--warning) / 0.32);
  background: hsl(var(--warning) / 0.1);
  color: hsl(var(--warning));
}

.subscription-sidebar__list {
  position: relative;
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 0.5rem;
}

.subscription-sidebar__channel {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.625rem;
  width: 100%;
  min-height: 2.75rem;
  padding: 0 0.625rem;
  overflow: hidden;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.875rem;
  text-align: left;
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.subscription-sidebar__channel + .subscription-sidebar__channel {
  margin-top: 0.25rem;
}

.subscription-sidebar__channel:hover {
  background: hsl(var(--accent) / 0.6);
  color: hsl(var(--foreground));
}

.subscription-sidebar__channel.is-active {
  border-color: hsl(var(--primary) / 0.2);
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.subscription-sidebar__active-avatar {
  box-shadow: 0 0 0 2px hsl(var(--primary) / 0.28);
}

.subscription-sidebar__channel-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 0.5rem;
  color: hsl(var(--warning));
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    opacity 0.16s ease;
}

.subscription-sidebar__channel-action:hover {
  background: hsl(var(--warning) / 0.1);
}

.subscription-sidebar__channel-action--ghost {
  position: absolute;
  top: 50%;
  right: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.55);
  opacity: 0;
  transform: translateY(-50%);
}

.subscription-sidebar__channel:hover .subscription-sidebar__channel-action--ghost,
.subscription-sidebar__channel:focus-within .subscription-sidebar__channel-action--ghost {
  opacity: 1;
}

.subscription-sidebar__channel-action--ghost:hover {
  background: hsl(var(--background));
  color: hsl(var(--foreground));
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

.subscription-sidebar__footer {
  flex: 0 0 auto;
  padding: 0.75rem;
  border-top: 1px solid hsl(var(--border) / 0.3);
  background: hsl(var(--background) / 0.52);
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
  .subscription-sidebar__search-icon,
  .subscription-sidebar__search-input,
  .subscription-sidebar__filter-button,
  .subscription-sidebar__special-filter,
  .subscription-sidebar__filter-chevron,
  .subscription-sidebar__site-option,
  .subscription-sidebar__channel,
  .subscription-sidebar__channel-action {
    transition: none;
  }
}
</style>
