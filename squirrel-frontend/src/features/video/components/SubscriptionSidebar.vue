<template>
  <div class="subscription-sidebar">
    <AppSidebarHeader title="订阅" :subtitle="`${total} 个频道`">
      <template #actions>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label="添加订阅频道"
          title="添加订阅频道"
          @click="$emit('add')"
        >
          <AppIcon name="plus" class="h-4 w-4" />
        </Button>
      </template>
    </AppSidebarHeader>

    <div class="app-pane__controls app-pane__controls--compact">
      <AppSearchInput
        :model-value="search"
        placeholder="搜索频道..."
        aria-label="搜索频道"
        @update:model-value="$emit('update:search', $event)"
      />

      <div class="subscription-sidebar__filters">
        <Select
          :model-value="site || 'all'"
          @update:model-value="$emit('update:site', String($event) === 'all' ? '' : String($event))"
        >
          <SelectTrigger
            class="subscription-sidebar__source-select"
            :class="{ 'is-selected': site }"
            aria-label="按来源筛选频道"
          >
            <SelectValue placeholder="全部来源" />
          </SelectTrigger>
          <SelectContent class="min-w-48">
            <SelectItem value="all">全部来源</SelectItem>
            <SelectItem
              v-for="opt in siteOptions"
              :key="opt.value"
              :value="opt.value"
            >
              <span class="subscription-sidebar__source-option">
                <SiteIcon :site="opt.value" class="h-4 w-4 rounded-sm" />
                <span>{{ opt.label }}</span>
              </span>
            </SelectItem>
          </SelectContent>
        </Select>

        <Button
          type="button"
          variant="outline"
          size="sm"
          class="subscription-sidebar__filter-button subscription-sidebar__special-filter"
          :class="{ 'is-selected': specialFilter === 'yes' }"
          :aria-pressed="specialFilter === 'yes'"
          @click="$emit('toggle-special-filter')"
        >
          <AppIcon
            name="star"
            class="h-3.5 w-3.5"
          />
          <span>特别关注</span>
        </Button>

        <Button
          v-if="hasActiveFilters"
          type="button"
          variant="ghost"
          size="mini-icon"
          class="subscription-sidebar__clear"
          title="清除筛选"
          aria-label="清除筛选"
          @click="$emit('clear-filters')"
        >
          <AppIcon name="close" class="h-3.5 w-3.5" />
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

      <Button
        unstyled
        type="button"
        class="subscription-sidebar__item subscription-sidebar__overview"
        :class="{ 'is-selected': activeChannelId === null }"
        @click="$emit('select-all')"
      >
        <span class="subscription-sidebar__overview-icon">
          <AppIcon name="playlistVideo" class="h-4 w-4" />
        </span>
        <span class="subscription-sidebar__copy">
          <span class="subscription-sidebar__channel-name">全部动态</span>
          <span class="subscription-sidebar__meta">所有频道的近期发布</span>
        </span>
      </Button>

      <div
        v-for="sub in channels"
        :key="sub.id"
        class="subscription-sidebar__item"
        :class="{ 'is-selected': activeChannelId === sub.id }"
      >
        <Button
          unstyled
          type="button"
          class="subscription-sidebar__identity"
          :aria-current="activeChannelId === sub.id ? 'page' : undefined"
          @click="$emit('select-channel', sub.id)"
        >
          <SubscriptionAvatar
            :src="sub.avatar"
            :name="sub.name"
            size="md"
            class="subscription-sidebar__avatar"
          >
            <template v-if="sub.is_special_followed" #indicator>
              <span class="subscription-sidebar__special-dot" title="特别关注" />
            </template>
          </SubscriptionAvatar>

          <span class="subscription-sidebar__copy">
            <span class="subscription-sidebar__name-row">
              <span
                class="subscription-sidebar__channel-name"
                :class="{ 'has-unread': sub.unread_count > 0 }"
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
              <AppSpinner
                v-else-if="isSubscriptionSyncBusy(sub)"
                size="sm"
                class="subscription-sidebar__signal"
                title="同步中"
              />
            </span>

            <span class="subscription-sidebar__meta">
              <span v-if="sub.site" class="truncate">{{ sub.site }}</span>
              <template v-if="sub.pending_video_count > 0">
                <span v-if="sub.site" aria-hidden="true">·</span>
                <span>{{ sub.pending_video_count }} 待处理</span>
              </template>
            </span>
          </span>

          <span
            v-if="formatUnreadCount(sub.unread_count)"
            class="subscription-sidebar__unread app-mono"
            :title="`${sub.unread_count} 个未读`"
          >
            {{ formatUnreadCount(sub.unread_count) }}
          </span>
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="mini-icon"
          class="subscription-sidebar__channel-action"
          :class="{ 'is-active': sub.is_special_followed }"
          :disabled="togglingIds.has(sub.id)"
          :aria-pressed="sub.is_special_followed"
          :aria-label="sub.is_special_followed ? '取消特别关注' : '设为特别关注'"
          @click="$emit('toggle-special', sub)"
        >
          <AppSpinner v-if="togglingIds.has(sub.id)" size="sm" />
          <AppIcon
            v-else
            name="star"
            class="h-3.5 w-3.5"
          />
        </Button>
      </div>

      <div v-if="loading" class="subscription-sidebar__loading">
        <AppSkeleton v-for="i in 5" :key="i" height="3rem" rounded="var(--radius-lg)" shimmer />
      </div>

      <div ref="loadMoreRef" class="subscription-sidebar__load-more">
        <AppSpinner v-if="loadingMore" />
      </div>

      <div v-if="error && channels.length" class="subscription-sidebar__inline-error">
        <span class="truncate">{{ error }}</span>
        <Button variant="ghost" size="sm" @click="$emit('retry')">重试</Button>
      </div>

      <div
        v-if="!loading && !error && finished && !channels.length"
        class="subscription-sidebar__empty"
      >
        <span>{{ hasActiveFilters ? '没有匹配的频道' : '暂无频道' }}</span>
        <Button
          v-if="hasActiveFilters"
          variant="ghost"
          size="xs"
          @click="$emit('clear-filters')"
        >
          清除筛选
        </Button>
      </div>
    </div>

    <div v-if="channels.length || loading" class="app-pane__footer">
      <Button
        variant="ghost"
        size="sm"
        class="subscription-sidebar__import"
        @click="$emit('import')"
      >
        <AppIcon name="download" class="h-4 w-4" />
        导入已有订阅
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppSearchInput from '@/shared/components/layout/AppSearchInput.vue'
import AppSidebarHeader from '@/shared/components/layout/AppSidebarHeader.vue'
import { Button } from '@/shared/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/shared/ui/select'
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
  total: number
  loading: boolean
  loadingMore: boolean
  finished: boolean
  error?: string | null
  search: string
  site: string
  siteOptions: { value: string; label: string }[]
  specialFilter: 'all' | 'yes'
  activeChannelId: string | number | null
  togglingIds?: Set<string | number>
}>()

defineEmits<{
  add: []
  import: []
  retry: []
  'clear-filters': []
  'select-all': []
  'select-channel': [id: string | number]
  'toggle-special': [sub: SubscriptionListItem]
  'toggle-special-filter': []
  'update:search': [value: string]
  'update:site': [value: string]
}>()

const togglingIds = computed(() => props.togglingIds ?? new Set<string | number>())
const hasActiveFilters = computed(() => (
  Boolean(props.site)
  || props.specialFilter === 'yes'
  || Boolean(props.search.trim())
))

const listContainerRef = ref<HTMLElement | null>(null)
const loadMoreRef = ref<HTMLElement | null>(null)
defineExpose({ listContainer: listContainerRef, loadMore: loadMoreRef })
</script>

<style scoped>
.subscription-sidebar {
  display: flex;
  width: 100%;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
}

.subscription-sidebar__filters {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.subscription-sidebar__source-select {
  min-width: 0;
  width: auto;
  height: 2rem;
  flex: 1 1 auto;
  border-color: hsl(var(--border) / 0.58);
  background: hsl(var(--muted) / 0.28);
  padding-inline: 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
  box-shadow: none;
}

.subscription-sidebar__filter-button {
  min-width: 0;
  height: 2rem;
  justify-content: flex-start;
  gap: 0.4rem;
  border-color: hsl(var(--border) / 0.58);
  background: hsl(var(--muted) / 0.28);
  padding-inline: 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 500;
}

.subscription-sidebar__source-select:hover {
  background: hsl(var(--muted) / 0.48);
  color: hsl(var(--foreground));
}

.subscription-sidebar__filter-button:hover {
  background: hsl(var(--muted) / 0.48);
  color: hsl(var(--foreground));
}

.subscription-sidebar__filter-button.is-selected,
.subscription-sidebar__source-select.is-selected {
  border-color: hsl(var(--primary) / 0.28);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--foreground));
}

.subscription-sidebar__special-filter.is-selected {
  border-color: hsl(var(--foreground) / 0.12);
  background: hsl(var(--foreground) / 0.045);
  color: hsl(var(--foreground) / 0.72);
}

.subscription-sidebar__source-option {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
}

.subscription-sidebar__clear {
  flex: none;
  color: hsl(var(--muted-foreground));
}

.subscription-sidebar__item {
  display: flex;
  width: 100%;
  min-height: 3rem;
  align-items: center;
  gap: 0.625rem;
  border: 1px solid transparent;
  border-radius: var(--radius-lg);
  padding: 0 0.375rem 0 0.625rem;
  color: hsl(var(--muted-foreground));
  transition:
    color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default);
}

.subscription-sidebar__item + .subscription-sidebar__item {
  margin-top: 0.25rem;
}

.subscription-sidebar__item:hover,
.subscription-sidebar__item:focus-within {
  background: hsl(var(--accent) / 0.6);
  color: hsl(var(--foreground));
}

.subscription-sidebar__item.is-selected {
  border-color: hsl(var(--primary) / 0.2);
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
}

.subscription-sidebar__identity {
  display: flex;
  min-width: 0;
  min-height: 2.875rem;
  flex: 1 1 auto;
  align-items: center;
  gap: 0.625rem;
  color: inherit;
  text-align: left;
  cursor: pointer;
}

.subscription-sidebar__identity:focus-visible,
.subscription-sidebar__overview:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px hsl(var(--background)), 0 0 0 4px hsl(var(--ring) / 0.42);
}

.subscription-sidebar__overview {
  justify-content: flex-start;
  margin-bottom: 0.5rem;
  border-bottom: 1px solid var(--app-hairline);
  border-radius: 0;
  color: hsl(var(--muted-foreground));
  text-align: left;
  cursor: pointer;
}

.subscription-sidebar__overview + .subscription-sidebar__item {
  margin-top: 0;
}

.subscription-sidebar__overview-icon {
  display: inline-flex;
  width: 1.75rem;
  height: 1.75rem;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.52);
  color: hsl(var(--muted-foreground));
}

.subscription-sidebar__avatar {
  position: relative;
  flex: none;
  box-shadow: 0 0 0 1px var(--app-surface-border-subtle);
}

.subscription-sidebar__special-dot {
  position: absolute;
  right: -0.05rem;
  bottom: -0.05rem;
  width: 0.4rem;
  height: 0.4rem;
  border: 1px solid hsl(var(--background));
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.62);
}

.subscription-sidebar__copy {
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 0.125rem;
}

.subscription-sidebar__name-row {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.35rem;
}

.subscription-sidebar__channel-name {
  min-width: 0;
  overflow: hidden;
  color: hsl(var(--foreground) / 0.82);
  font-size: 0.8125rem;
  font-weight: 500;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.subscription-sidebar__channel-name.has-unread {
  color: hsl(var(--foreground));
  font-weight: 650;
}

.subscription-sidebar__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.25rem;
  color: hsl(var(--muted-foreground) / 0.75);
  font-size: 0.625rem;
  font-weight: 500;
  line-height: 1.2;
}

.subscription-sidebar__signal {
  flex: none;
}

.subscription-sidebar__signal--error {
  color: hsl(var(--destructive));
}

.subscription-sidebar__unread {
  flex: none;
  min-width: 1.75rem;
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.625rem;
  font-weight: 600;
  line-height: 1;
  text-align: right;
}

.subscription-sidebar__channel-action {
  flex: none;
  opacity: 0;
  color: hsl(var(--muted-foreground) / 0.52);
}

.subscription-sidebar__channel-action.is-active {
  opacity: 0.72;
  color: hsl(var(--foreground) / 0.72);
}

.subscription-sidebar__item:hover .subscription-sidebar__channel-action,
.subscription-sidebar__item:focus-within .subscription-sidebar__channel-action {
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
  width: 100%;
  height: 2.5rem;
  align-items: center;
  justify-content: center;
}

.subscription-sidebar__state {
  padding: 0.5rem;
}

.subscription-sidebar__empty {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
  padding: 0.75rem 0.625rem;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.75rem;
  font-weight: 500;
}

.subscription-sidebar__inline-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin: 0.5rem;
  border: 1px solid hsl(var(--destructive) / 0.22);
  border-radius: var(--radius-md);
  background: hsl(var(--destructive) / 0.06);
  padding: 0.45rem 0.6rem;
  color: hsl(var(--destructive));
  font-size: 0.75rem;
  font-weight: 500;
}

.subscription-sidebar__import {
  width: 100%;
  height: 2rem;
  justify-content: flex-start;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground));
}

.subscription-sidebar__item.is-selected .subscription-sidebar__channel-name {
  color: hsl(var(--foreground));
}

.subscription-sidebar__item.is-selected .subscription-sidebar__overview-icon {
  background: hsl(var(--primary) / 0.14);
  color: hsl(var(--primary));
}

@media (prefers-reduced-motion: reduce) {
  .subscription-sidebar__item {
    transition: none;
  }

  .subscription-sidebar__channel-action {
    opacity: 1;
  }
}
</style>
