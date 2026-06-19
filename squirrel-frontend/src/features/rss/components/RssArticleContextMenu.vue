<template>
  <Teleport to="body">
    <div
      v-if="visible && entry"
      ref="rootRef"
      role="menu"
      aria-label="文章操作"
      class="fixed z-[9999] w-[200px] rounded-xl border border-border/30 bg-popover/90 backdrop-blur-xl p-1.5 shadow-[0_6px_20px_rgba(0,0,0,0.06)] dark:shadow-[0_10px_30px_rgba(0,0,0,0.18)] animate-fade-in"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
    >
      <div class="flex flex-col gap-0.5">
        <button
          role="menuitem"
          @click="$emit('toggleRead', entry)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon :name="entry.is_read ? 'eyeOff' : 'eye'" class="h-3.5 w-3.5 opacity-70" />
          <span>{{ entry.is_read ? '标记为未读' : '标记为已读' }}</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('toggleStar', entry)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="star" class="h-3.5 w-3.5 opacity-70" :class="entry.is_starred ? 'text-amber-500 fill-amber-500' : ''" />
          <span>{{ entry.is_starred ? '取消收藏' : '收藏文章' }}</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('goToFeed', entry)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="inbox" class="h-3.5 w-3.5 opacity-70" />
          <span>查看订阅源</span>
        </button>

        <div class="h-px bg-border/20 my-1" role="separator"></div>

        <template v-if="feed">
          <div class="px-2.5 py-1 text-[9px] font-bold text-muted-foreground uppercase tracking-wider" role="group" aria-label="默认打开方式">默认打开方式</div>

          <button
            role="menuitemradio"
            :aria-checked="!feed.open_method"
            @click="$emit('setOpenMethod', feed, null)"
            class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">内嵌阅读</span>
            <AppIcon v-if="!feed.open_method" name="check" class="h-3 w-3 text-primary" />
          </button>

          <button
            role="menuitemradio"
            :aria-checked="feed.open_method === 'app_browser'"
            @click="$emit('setOpenMethod', feed, 'app_browser')"
            class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="siteFallback" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">应用内浏览器</span>
            <AppIcon v-if="feed.open_method === 'app_browser'" name="check" class="h-3 w-3 text-primary" />
          </button>

          <button
            role="menuitemradio"
            :aria-checked="feed.open_method === 'external_browser'"
            @click="$emit('setOpenMethod', feed, 'external_browser')"
            class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
          >
            <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">系统浏览器</span>
            <AppIcon v-if="feed.open_method === 'external_browser'" name="check" class="h-3 w-3 text-primary" />
          </button>
        </template>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'above', true)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
          <span>上方全部已读</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'below', true)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
          <span>下方全部已读</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'all', true)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
          <span>列表全部已读</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'all', false)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="eyeOff" class="h-3.5 w-3.5 opacity-70" />
          <span>列表全部未读</span>
        </button>

        <div class="h-px bg-border/20 my-1" role="separator"></div>

        <button
          role="menuitem"
          @click="$emit('unsubscribe', entry)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-destructive cursor-pointer"
        >
          <AppIcon name="close" class="h-3.5 w-3.5 opacity-70" />
          <span>取消订阅该源</span>
        </button>

        <div class="h-px bg-border/20 my-1" role="separator"></div>

        <button
          role="menuitem"
          @click="$emit('copyLink', entry)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="link" class="h-3.5 w-3.5 opacity-70" />
          <span>复制文章链接</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('openExternal', entry)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
          <span>在外部浏览器打开</span>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { RssEntry, RssFeed, ReadBatchMode } from '@/features/rss/composables/rssTypes'

defineProps<{
  visible: boolean
  entry: RssEntry | null
  // ponytail: the parent resolves the entry's feed once (findFeedByEntry) and
  // passes it in, instead of the child re-calling the lookup 4 times.
  feed: RssFeed | null
  position: { x: number; y: number }
}>()

defineEmits<{
  toggleRead: [entry: RssEntry]
  toggleStar: [entry: RssEntry]
  goToFeed: [entry: RssEntry]
  setOpenMethod: [feed: RssFeed, method: string | null]
  // scope: 'above' | 'below' | 'all', read: true=read / false=unread
  batchRead: [scope: ReadBatchMode, read: boolean]
  unsubscribe: [entry: RssEntry]
  copyLink: [entry: RssEntry]
  openExternal: [entry: RssEntry]
}>()

// ponytail: expose the rendered menu div so useRssEntries can still measure it
// for overflow repositioning after the template moved into this child.
const rootRef = ref<HTMLElement | null>(null)
defineExpose({ rootRef })
</script>
