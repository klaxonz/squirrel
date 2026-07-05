<template>
  <div class="feed-folder-tree custom-scrollbar">
    <div class="feed-folder-tree__all" :class="{ 'is-selected': !selectedFeedId }">
      <button
        @click="$emit('selectAll')"
        class="feed-folder-tree__all-button"
      >
        <AppIcon name="inbox" class="h-3.5 w-3.5 shrink-0" />
        <span class="truncate">全部订阅</span>
        <span class="feed-folder-tree__total">{{ totalFeeds }}</span>
      </button>
      <button
        v-if="hasAccount"
        @click="$emit('addFeed')"
        class="feed-folder-tree__add"
        title="添加订阅源"
      >
        <AppIcon name="plus" class="h-3.5 w-3.5" />
      </button>
    </div>

    <div class="feed-folder-tree__separator"></div>

    <div v-for="folder in folders" :key="folder.name" class="feed-folder-tree__folder">
      <button
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
      </button>

      <div v-if="expandedFolders[folder.name]" class="feed-folder-tree__feeds">
        <button
          v-for="feed in folder.feeds"
          :key="feed.id"
          @click="$emit('selectFeed', feed.id)"
          @contextmenu.prevent.stop="$emit('feedContextMenu', feed, $event)"
          class="feed-folder-tree__feed"
          :class="{ 'is-selected': selectedFeedId === feed.id }"
        >
          <SiteIcon :icon-url="feed.icon_url || null" size="xs" rounded="sm" class="shrink-0" />
          <span class="flex-1 truncate">{{ feed.title }}</span>
          <button
            @click.stop="$emit('unsubscribeFeed', feed)"
            class="feed-folder-tree__remove"
            title="取消订阅"
          >
            <AppIcon name="close" class="h-3 w-3" />
          </button>
        </button>
      </div>
    </div>

    <div v-if="!folders.length" class="feed-folder-tree__empty">
      暂无匹配订阅源
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import type { RssFeed } from '@/features/rss/composables/rssTypes'

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
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 0.75rem;
}

.feed-folder-tree__all,
.feed-folder-tree__feed {
  display: flex;
  align-items: center;
  width: 100%;
  min-height: 2rem;
  border: 1px solid transparent;
  border-radius: 0.5rem;
  color: hsl(var(--muted-foreground));
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    border-color 0.16s ease;
}

.feed-folder-tree__all.is-selected,
.feed-folder-tree__feed.is-selected {
  color: hsl(var(--primary));
  font-weight: 650;
  background: hsl(var(--primary) / 0.08);
  border-color: hsl(var(--primary) / 0.18);
}

.feed-folder-tree__all-button,
.feed-folder-tree__feed {
  text-align: left;
}

.feed-folder-tree__all-button {
  display: flex;
  flex: 1 1 auto;
  align-items: center;
  gap: 0.75rem;
  height: 100%;
  min-width: 0;
  padding: 0 0.625rem;
  overflow: hidden;
  font-size: 0.75rem;
}

.feed-folder-tree__total {
  margin-left: auto;
  font-size: 0.75rem;
  opacity: 0.65;
}

.feed-folder-tree__add,
.feed-folder-tree__remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 auto;
  border-radius: 0.375rem;
  color: hsl(var(--muted-foreground) / 0.62);
  transition:
    color 0.16s ease,
    background-color 0.16s ease,
    opacity 0.16s ease;
}

.feed-folder-tree__add {
  margin-right: 0.25rem;
  padding: 0.25rem;
}

.feed-folder-tree__add:hover {
  color: hsl(var(--primary));
  background: hsl(var(--primary) / 0.1);
}

.feed-folder-tree__separator {
  height: 1px;
  margin: 0.625rem 0;
  background: hsl(var(--border) / 0.22);
}

.feed-folder-tree__folder {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.feed-folder-tree__folder + .feed-folder-tree__folder {
  margin-top: 0.25rem;
}

.feed-folder-tree__folder-button {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  padding: 0.375rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 650;
  color: hsl(var(--muted-foreground));
  transition: color 0.16s ease;
}

.feed-folder-tree__folder-button:hover {
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
  min-width: 1.375rem;
  padding: 0.125rem 0.375rem;
  border: 1px solid hsl(var(--border) / 0.28);
  border-radius: 0.375rem;
  background: hsl(var(--accent) / 0.42);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  line-height: 1.1;
  text-align: center;
}

.feed-folder-tree__feeds {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
  padding-left: 0.75rem;
}

.feed-folder-tree__feed {
  position: relative;
  gap: 0.625rem;
  padding: 0 0.625rem;
  overflow: hidden;
  font-size: 0.75rem;
}

.feed-folder-tree__feed:not(.is-selected):hover {
  color: hsl(var(--foreground));
  background: hsl(var(--accent) / 0.58);
}

.feed-folder-tree__remove {
  padding: 0.125rem;
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

@media (prefers-reduced-motion: reduce) {
  .feed-folder-tree__all,
  .feed-folder-tree__feed,
  .feed-folder-tree__add,
  .feed-folder-tree__remove,
  .feed-folder-tree__folder-button,
  .feed-folder-tree__chevron {
    transition: none;
  }
}
</style>
