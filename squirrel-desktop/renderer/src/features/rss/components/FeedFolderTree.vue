<template>
  <div class="feed-folder-tree custom-scrollbar" :aria-busy="loading">
    <div class="feed-folder-tree__all" :class="{ 'is-selected': !selectedFeedId }">
      <Button
        text severity="secondary"
        size="sm"
        :disabled="loading"
        @click="$emit('selectAll')"
        class="feed-folder-tree__all-button"
      >
        <AppIcon name="inbox" class="h-3.5 w-3.5 shrink-0" />
        <span class="truncate">全部订阅</span>
        <span class="feed-folder-tree__total">
          <AppSkeleton
            v-if="loading"
            width="0.875rem"
            height="0.625rem"
            rounded="var(--radius-sm)"
            shimmer
          />
          <template v-else>{{ totalFeeds }}</template>
        </span>
      </Button>
      <Button
        v-if="hasAccount"
        text severity="secondary"
        size="sm" icon-only
        @click="$emit('addFeed')"
        class="feed-folder-tree__add"
        title="添加订阅源"
      >
        <AppIcon name="plus" class="h-3.5 w-3.5" />
      </Button>
    </div>

    <div class="feed-folder-tree__separator"></div>

    <FeedFolderTreeSkeleton v-if="loading" />

    <template v-else>
      <div class="feed-folder-tree__folders">
        <div v-for="folder in folders" :key="folder.name" class="feed-folder-tree__folder">
          <Button
            text severity="secondary"
            size="sm"
            @click="$emit('toggleFolder', folder.name)"
            class="feed-folder-tree__folder-button"
          >
            <div class="flex items-center gap-1.5 min-w-0">
              <AppIcon
                name="chevronRight"
                class="feed-folder-tree__chevron"
                :class="{ 'rotate-90': expandedFolders[folder.name] }"
              />
              <span class="truncate">{{ folder.name }}</span>
            </div>
            <span class="feed-folder-tree__count">{{ folder.feeds.length }}</span>
          </Button>

          <div v-if="expandedFolders[folder.name]" class="feed-folder-tree__feeds">
            <div
              v-for="feed in folder.feeds"
              :key="feed.id"
              role="button"
              tabindex="0"
              @click="$emit('selectFeed', feed.id)"
              @keydown.enter.prevent="$emit('selectFeed', feed.id)"
              @keydown.space.prevent="$emit('selectFeed', feed.id)"
              @contextmenu.prevent.stop="$emit('feedContextMenu', feed, $event)"
              class="feed-folder-tree__feed"
              :class="{ 'is-selected': selectedFeedId === feed.id }"
            >
              <SiteIcon :icon-url="feed.icon_url || null" size="xs" rounded="sm" class="shrink-0" />
              <span class="flex-1 truncate">{{ feed.title }}</span>
              <Button
                text severity="secondary"
                size="sm" icon-only
                @click.stop="$emit('unsubscribeFeed', feed)"
                class="feed-folder-tree__remove"
                title="取消订阅"
              >
                <AppIcon name="close" class="h-3 w-3" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="!folders.length" class="feed-folder-tree__empty">
        暂无匹配订阅源
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import { Button } from '@/shared/ui/button'
import type { RssFeed } from '@/features/rss/composables/rssTypes'
import FeedFolderTreeSkeleton from './FeedFolderTreeSkeleton.vue'

interface FeedFolder {
  name: string
  feeds: RssFeed[]
}

defineProps<{
  folders: FeedFolder[]
  expandedFolders: Record<string, boolean>
  selectedFeedId: number | null
  totalFeeds: number
  hasAccount: boolean
  loading: boolean
}>()

defineEmits<{
  selectAll: []
  addFeed: []
  toggleFolder: [name: string]
  selectFeed: [id: number]
  feedContextMenu: [feed: RssFeed, event: MouseEvent]
  unsubscribeFeed: [feed: RssFeed]
}>()
</script>

<style scoped>
.feed-folder-tree {
  display: flex;
  min-height: 0;
  flex: 1 1 auto;
  flex-direction: column;
  overflow-y: auto;
  padding: var(--space-3);
}

.feed-folder-tree__all,
.feed-folder-tree__feed {
  position: relative;
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 2.125rem;
  border: 0;
  border-radius: var(--radius-md);
  color: hsl(var(--muted-foreground) / 0.9);
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}

.feed-folder-tree__all.is-selected,
.feed-folder-tree__feed.is-selected {
  color: hsl(var(--foreground));
  font-weight: 650;
  background: hsl(var(--accent) / 0.62);
}

.feed-folder-tree__all-button,
.feed-folder-tree__feed {
  text-align: left;
}

.feed-folder-tree__all-button {
  flex: 1 1 auto;
  justify-content: flex-start;
  gap: 0.75rem;
  height: 100%;
  min-width: 0;
  padding: 0 0.625rem 0 0.75rem;
  overflow: hidden;
  font-size: 0.8125rem;
}

.feed-folder-tree__total {
  margin-left: auto;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.75rem;
}

.feed-folder-tree__add,
.feed-folder-tree__remove {
  flex: 0 0 auto;
  border-radius: 0.375rem;
  color: hsl(var(--muted-foreground) / 0.62);
}

.feed-folder-tree__add {
  margin-right: 0.25rem;
  padding: 0.25rem;
}

.feed-folder-tree__add:hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent) / 0.58);
}

.feed-folder-tree__separator {
  height: 1px;
  margin: 0.75rem 0;
  background: hsl(var(--border) / 0.22);
}

.feed-folder-tree__folders {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.feed-folder-tree__folder {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.feed-folder-tree__folder-button {
  justify-content: space-between;
  width: 100%;
  min-height: 2rem;
  padding: 0.25rem 0.625rem;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--muted-foreground) / 0.9);
}

.feed-folder-tree__folder-button:hover {
  background: hsl(var(--accent) / 0.35);
  color: hsl(var(--foreground));
}

.feed-folder-tree__chevron {
  flex: 0 0 auto;
  width: 0.75rem;
  height: 0.75rem;
  color: hsl(var(--muted-foreground) / 0.72);
  transition: transform 0.16s ease;
}

.feed-folder-tree__count {
  flex: 0 0 auto;
  min-width: 1.25rem;
  color: hsl(var(--muted-foreground) / 0.8);
  font-size: 0.75rem;
  line-height: 1.1;
  text-align: right;
}

.feed-folder-tree__feeds {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding: 0.125rem 0 0.25rem 0.75rem;
}

.feed-folder-tree__feed {
  position: relative;
  gap: 0.625rem;
  padding: 0 0.5rem 0 0.75rem;
  overflow: hidden;
  font-size: 0.8125rem;
  cursor: pointer;
}

.feed-folder-tree__feed:not(.is-selected):hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent) / 0.58);
}

.feed-folder-tree__remove {
  opacity: 0;
}

.feed-folder-tree__feed:hover .feed-folder-tree__remove,
.feed-folder-tree__feed:focus-within .feed-folder-tree__remove {
  opacity: 1;
}

.feed-folder-tree__remove:hover {
  color: hsl(var(--destructive));
  background: hsl(var(--destructive) / 0.1);
}

.feed-folder-tree__empty {
  padding: 2.5rem 0.75rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  text-align: center;
}

@media (hover: none), (prefers-reduced-motion: reduce) {
  .feed-folder-tree__remove {
    opacity: 1;
  }
}

@media (prefers-reduced-motion: reduce) {
  .feed-folder-tree__all,
  .feed-folder-tree__feed,
  .feed-folder-tree__chevron {
    transition: none;
  }
}
</style>
