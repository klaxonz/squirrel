<template>
  <Teleport to="body">
    <div
      v-if="visible && feed"
      ref="rootRef"
      class="fixed z-[9999] w-[200px] rounded-xl border border-border/30 bg-popover/90 backdrop-blur-xl p-1.5 shadow-[0_6px_20px_rgba(0,0,0,0.06)] dark:shadow-[0_10px_30px_rgba(0,0,0,0.18)] animate-fade-in"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
    >
      <div class="flex flex-col gap-0.5">
        <button
          @click="$emit('markAllRead', feed)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
          <span>全部标记为已读</span>
        </button>

        <button
          @click="$emit('syncFeed', feed)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="refresh" class="h-3.5 w-3.5 opacity-70" />
          <span>同步文章</span>
        </button>

        <button
          @click="$emit('copyLink', feed)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="link" class="h-3.5 w-3.5 opacity-70" />
          <span>复制订阅源地址</span>
        </button>

        <button
          v-if="feed.site_url"
          @click="$emit('openSite', feed)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
          <span>访问源网站</span>
        </button>

        <div class="h-px bg-border/20 my-1"></div>

        <div class="px-2.5 py-1 text-[9px] font-bold text-muted-foreground uppercase tracking-wider">默认打开方式</div>

        <button
          @click="$emit('setOpenMethod', feed, null)"
          class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
          <span class="flex-1">内嵌阅读</span>
          <AppIcon v-if="!feed.open_method" name="check" class="h-3 w-3 text-primary" />
        </button>

        <button
          @click="$emit('setOpenMethod', feed, 'app_browser')"
          class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="siteFallback" class="h-3.5 w-3.5 opacity-70" />
          <span class="flex-1">应用内浏览器</span>
          <AppIcon v-if="feed.open_method === 'app_browser'" name="check" class="h-3 w-3 text-primary" />
        </button>

        <button
          @click="$emit('setOpenMethod', feed, 'external_browser')"
          class="flex h-7 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-foreground cursor-pointer"
        >
          <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
          <span class="flex-1">系统浏览器</span>
          <AppIcon v-if="feed.open_method === 'external_browser'" name="check" class="h-3 w-3 text-primary" />
        </button>

        <div class="h-px bg-border/20 my-1"></div>

        <button
          @click="$emit('unsubscribe', feed)"
          class="flex h-8 items-center gap-2 rounded-lg px-2.5 text-left text-xs font-medium transition-colors hover:bg-accent text-destructive cursor-pointer"
        >
          <AppIcon name="close" class="h-3.5 w-3.5 opacity-70" />
          <span>取消订阅</span>
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import type { RssFeed } from '@/composables/rssTypes'

defineProps<{
  visible: boolean
  feed: RssFeed | null
  position: { x: number; y: number }
}>()

defineEmits<{
  markAllRead: [feed: RssFeed]
  syncFeed: [feed: RssFeed]
  copyLink: [feed: RssFeed]
  openSite: [feed: RssFeed]
  // open_method values: null = in-app reader, 'app_browser', 'external_browser'
  setOpenMethod: [feed: RssFeed, method: string | null]
  unsubscribe: [feed: RssFeed]
}>()

// ponytail: expose the rendered menu div so the parent's composable
// (useRssFeeds) can still measure it for overflow repositioning after the
// template moved into this child component.
const rootRef = ref<HTMLElement | null>(null)
defineExpose({ rootRef })
</script>
