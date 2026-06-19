<template>
  <div class="flex-1 space-y-1 overflow-y-auto p-3 custom-scrollbar">
    <div
      class="flex h-8 w-full items-center rounded-lg px-2.5 transition-all"
      :class="!selectedFeedId ? 'bg-transparent text-primary font-semibold' : 'text-muted-foreground'"
    >
      <button
        @click="$emit('selectAll')"
        class="flex flex-1 items-center gap-3 text-left text-xs overflow-hidden h-full"
      >
        <AppIcon name="inbox" class="h-3.5 w-3.5 shrink-0" />
        <span class="truncate">全部订阅</span>
        <span class="text-xs opacity-60 ml-auto">{{ totalFeeds }}</span>
      </button>
      <button
        v-if="hasAccount"
        @click="$emit('addFeed')"
        class="shrink-0 ml-1 rounded-md p-1 text-muted-foreground/50 hover:text-primary hover:bg-primary/10 transition-all"
        title="添加订阅源"
      >
        <AppIcon name="plus" class="h-3.5 w-3.5" />
      </button>
    </div>

    <div class="h-px bg-border/20 my-2"></div>

    <div v-for="folder in folders" :key="folder.name" class="space-y-1">
      <button
        @click="$emit('toggleFolder', folder.name)"
        class="flex w-full items-center justify-between px-3 py-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
      >
        <div class="flex items-center gap-1.5 min-w-0">
          <AppIcon
            name="chevronRight"
            class="h-3 w-3 transition-transform text-muted-foreground/70 shrink-0"
            :class="{ 'rotate-90': expandedFolders[folder.name] }"
          />
          <span class="truncate">{{ folder.name }}</span>
        </div>
        <span class="text-[10px] bg-accent/60 px-1.5 py-0.5 rounded-full text-muted-foreground/80 shrink-0">{{ folder.feeds.length }}</span>
      </button>

      <div v-if="expandedFolders[folder.name]" class="pl-3 space-y-0.5">
        <button
          v-for="feed in folder.feeds"
          :key="feed.id"
          @click="$emit('selectFeed', feed.id)"
          @contextmenu.prevent.stop="$emit('feedContextMenu', feed, $event)"
          class="group relative flex h-8 w-full items-center gap-2.5 rounded-lg px-2.5 text-left text-xs transition-all overflow-hidden"
          :class="selectedFeedId === feed.id ? 'bg-transparent text-primary font-semibold' : 'text-muted-foreground hover:bg-accent/60 hover:text-foreground'"
        >
          <SiteIcon :icon-url="feed.icon_url || null" size="xs" rounded="sm" class="shrink-0" />
          <span class="flex-1 truncate">{{ feed.title }}</span>
          <button
            @click.stop="$emit('unsubscribeFeed', feed)"
            class="shrink-0 rounded p-0.5 text-muted-foreground/40 hover:text-destructive hover:bg-destructive/10 opacity-0 group-hover:opacity-100 transition-all"
            title="取消订阅"
          >
            <AppIcon name="close" class="h-3 w-3" />
          </button>
        </button>
      </div>
    </div>

    <div v-if="!folders.length" class="py-10 text-center text-xs text-muted-foreground">
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
