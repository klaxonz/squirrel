<template>
  <!-- Fills AppTwoColumnLayout sidebar slot — chrome (border/bg/width) lives on the shell. -->
  <div class="subscription-sidebar">
    <AppSidebarHeader title="订阅频道" :subtitle="`${total} 个频道`">
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
            aria-label="按来源筛选"
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
          <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': specialFilter === 'yes' }" />
          <span>特别关注</span>
        </Button>
      </div>
    </div>

    <div ref="listContainerRef" class="app-pane__list custom-scrollbar">
      <div v-if="error && !channels.length" class="subscription-sidebar__state">
        <AppEmptyState variant="error" title="加载失败" :copy="error">
          <template #actions>
            <Button variant="outline" size="sm" @click="$emit('retry')">重试</Button>
          </template>
        </AppEmptyState>
      </div>

      <AppSelectableListItem
        v-for="sub in channels"
        :key="sub.id"
        :selected="activeChannelId === sub.id"
        class="subscription-sidebar__item"
        @click="$emit('select-channel', sub.id)"
        @keydown.enter.prevent="$emit('select-channel', sub.id)"
        @keydown.space.prevent="$emit('select-channel', sub.id)"
      >
        <div class="subscription-sidebar__avatar-wrap">
          <SubscriptionAvatar
            :src="sub.avatar"
            :name="sub.name"
            size="md"
            :class="activeChannelId === sub.id ? 'subscription-sidebar__active-avatar' : ''"
          />
          <span
            v-if="formatUnreadCount(sub.unread_count)"
            class="subscription-sidebar__unread-dot app-mono"
            :title="`${sub.unread_count} 个未读`"
          >
            {{ formatUnreadCount(sub.unread_count) }}
          </span>
        </div>

        <div class="subscription-sidebar__channel-meta min-w-0 flex-1">
          <div class="subscription-sidebar__name-row">
            <span
              class="subscription-sidebar__channel-name"
              :class="{ 'is-active': activeChannelId === sub.id }"
            >
              {{ sub.name }}
            </span>
            <span
              v-if="isSubscriptionSyncFailed(sub)"
              class="subscription-sidebar__signal subscription-sidebar__signal--error"
              :title="subscriptionSyncErrorLabel(sub)"
              aria-label="同步失败"
            >
              <AppIcon name="warning" class="h-3 w-3" />
            </span>
            <span
              v-else-if="isSubscriptionSyncBusy(sub)"
              class="subscription-sidebar__signal subscription-sidebar__signal--busy"
              title="同步中"
              aria-label="同步中"
            >
              <span class="subscription-sidebar__busy-dot" />
            </span>
          </div>
        </div>

        <Button
          type="button"
          variant="ghost"
          size="mini-icon"
          class="subscription-sidebar__channel-action"
          :class="sub.is_special_followed ? 'is-pinned' : 'subscription-sidebar__channel-action--ghost'"
          :disabled="togglingIds.has(sub.id)"
          :aria-pressed="sub.is_special_followed"
          :aria-label="sub.is_special_followed ? '取消特别关注' : '设为特别关注'"
          @click.stop="$emit('toggle-special', sub)"
        >
          <AppSpinner v-if="togglingIds.has(sub.id)" size="sm" />
          <AppIcon
            v-else
            name="star"
            class="h-3.5 w-3.5"
            :class="{ 'fill-current': sub.is_special_followed }"
          />
        </Button>
      </AppSelectableListItem>

      <div v-if="loading" class="subscription-sidebar__loading">
        <AppSkeleton v-for="i in 5" :key="i" height="2.5rem" rounded="var(--radius-md)" shimmer />
      </div>

      <div ref="loadMoreRef" class="subscription-sidebar__load-more">
        <AppSpinner v-if="loadingMore" />
      </div>

      <div v-if="error && channels.length" class="subscription-sidebar__inline-error">
        <span class="truncate">{{ error }}</span>
        <Button variant="ghost" size="sm" @click="$emit('retry')">重试</Button>
      </div>

      <AppEmptyState
        v-if="!loading && !error && finished && !channels.length"
        class="py-10"
        variant="plain"
        icon="inbox"
        :title="hasActiveFilters ? '暂无匹配订阅' : '还没有订阅'"
        :copy="hasActiveFilters ? '请尝试更换筛选条件，或清除搜索。' : '添加频道地址，或从站点导入已有订阅。'"
      >
        <template v-if="!hasActiveFilters" #actions>
          <Button size="sm" @click="$emit('add')">添加订阅</Button>
          <Button size="sm" variant="outline" @click="$emit('import')">导入订阅</Button>
        </template>
        <template v-else #actions>
          <Button size="sm" variant="outline" @click="$emit('clear-filters')">清除筛选</Button>
        </template>
      </AppEmptyState>
    </div>

    <div class="app-pane__footer">
      <Button variant="outline" class="subscription-sidebar__import" @click="$emit('import')">
        <AppIcon name="download" class="mr-2 h-4 w-4 text-muted-foreground" />
        导入订阅
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * Subscription channel sidebar for the Subscribed view. Pure presentational +
 * controlled: the parent owns all state and passes it down via props.
 */
import { computed, ref } from 'vue'
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
import {
  formatUnreadCount,
  isSubscriptionSyncBusy,
  isSubscriptionSyncFailed,
  subscriptionSyncErrorLabel,
} from '@/features/video/lib/subscriptionPresenters'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

const props = defineProps<{
  channels: SubscriptionListItem[]
  /** Server-side total for the current filter (not the currently loaded page batch). */
  total: number
  loading: boolean
  loadingMore: boolean
  finished: boolean
  error?: string | null
  search: string
  site: string
  siteOptions: { value: string; label: string }[]
  activeSiteLabel: string
  siteDropdownOpen: boolean
  specialFilter: 'all' | 'yes'
  activeChannelId: string | number | null
  togglingIds?: Set<string | number>
}>()

const emit = defineEmits<{
  'add': []
  'import': []
  'retry': []
  'clear-filters': []
  'select-channel': [id: string | number]
  'toggle-special': [sub: SubscriptionListItem]
  'toggle-special-filter': []
  'update:search': [value: string]
  'update:site': [value: string]
  'update:siteDropdownOpen': [value: boolean]
}>()

const togglingIds = computed(() => props.togglingIds ?? new Set<string | number>())

const hasActiveFilters = computed(() => {
  return Boolean(props.site) || props.specialFilter === 'yes' || Boolean(props.search.trim())
})

const siteFilterRef = ref<HTMLElement | null>(null)
usePointerOutside(siteFilterRef, () => {
  emit('update:siteDropdownOpen', false)
})

const listContainerRef = ref<HTMLElement | null>(null)
const loadMoreRef = ref<HTMLElement | null>(null)
defineExpose({ listContainer: listContainerRef, loadMore: loadMoreRef })
</script>

<style scoped>
.subscription-sidebar {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  width: 100%;
}

.subscription-sidebar__item {
  min-height: 2.5rem;
}

.subscription-sidebar__avatar-wrap {
  position: relative;
  flex: none;
}

.subscription-sidebar__unread-dot {
  position: absolute;
  top: -0.2rem;
  right: -0.35rem;
  z-index: 1;
  min-width: 1rem;
  height: 1rem;
  padding: 0 0.25rem;
  border: 1px solid hsl(var(--background));
  border-radius: 999px;
  background: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
  font-size: 0.5625rem;
  font-weight: 700;
  line-height: 1rem;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.subscription-sidebar__channel-meta {
  min-width: 0;
}

.subscription-sidebar__name-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.35rem;
}

.subscription-sidebar__channel-name {
  display: block;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 500;
}

.subscription-sidebar__channel-name.is-active {
  font-weight: 600;
}

.subscription-sidebar__signal {
  display: inline-flex;
  flex: none;
  align-items: center;
  justify-content: center;
}

.subscription-sidebar__signal--error {
  color: hsl(var(--destructive) / 0.88);
}

.subscription-sidebar__signal--busy {
  width: 0.75rem;
  height: 0.75rem;
}

.subscription-sidebar__busy-dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.7);
  animation: subscription-sidebar-pulse 1.2s var(--ease-default) infinite;
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
  width: 1.625rem;
  height: 1.625rem;
  color: hsl(var(--muted-foreground) / 0.55);
}

.subscription-sidebar__channel-action.is-pinned {
  color: hsl(var(--warning));
}

.subscription-sidebar__channel-action--ghost {
  position: absolute;
  top: 50%;
  right: 0.45rem;
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
  gap: 0.375rem;
  padding: 0.5rem;
}

.subscription-sidebar__load-more {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 2.5rem;
}

.subscription-sidebar__state {
  padding: 0.5rem;
}

.subscription-sidebar__inline-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin: 0.5rem;
  padding: 0.45rem 0.6rem;
  border: 1px solid hsl(var(--destructive) / 0.22);
  border-radius: var(--radius-md);
  background: hsl(var(--destructive) / 0.06);
  color: hsl(var(--destructive) / 0.95);
  font-size: 0.75rem;
  font-weight: 500;
}

.subscription-sidebar__import {
  width: 100%;
  height: 2.25rem;
  justify-content: flex-start;
  border-color: hsl(var(--border) / 0.5);
  border-radius: var(--radius-lg);
  font-weight: 500;
}

.subscription-sidebar__import:hover {
  background: hsl(var(--background));
}

@keyframes subscription-sidebar-pulse {
  0%,
  100% {
    opacity: 0.35;
    transform: scale(0.9);
  }
  50% {
    opacity: 1;
    transform: scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .app-filter-trigger__chevron,
  .subscription-sidebar__busy-dot {
    animation: none;
    transition: none;
  }
}
</style>
