<template>
  <Teleport to="body">
    <div
      v-if="visible && feed"
      ref="rootRef"
      class="rss-feed-menu"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
    >
      <div class="rss-feed-menu__list">
        <button
          @click="$emit('markAllRead', feed)"
          class="rss-feed-menu__item"
        >
          <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
          <span>全部标记为已读</span>
        </button>

        <button
          @click="$emit('syncFeed', feed)"
          class="rss-feed-menu__item"
        >
          <AppIcon name="refresh" class="h-3.5 w-3.5 opacity-70" />
          <span>同步文章</span>
        </button>

        <button
          @click="$emit('copyLink', feed)"
          class="rss-feed-menu__item"
        >
          <AppIcon name="link" class="h-3.5 w-3.5 opacity-70" />
          <span>复制订阅源地址</span>
        </button>

        <button
          v-if="feed.site_url"
          @click="$emit('openSite', feed)"
          class="rss-feed-menu__item"
        >
          <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
          <span>访问源网站</span>
        </button>

        <div class="rss-feed-menu__separator"></div>

        <div class="rss-feed-menu__label">默认打开方式</div>

        <button
          @click="$emit('setOpenMethod', feed, null)"
          class="rss-feed-menu__item rss-feed-menu__item--compact"
        >
          <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
          <span class="flex-1">内嵌阅读</span>
          <AppIcon v-if="!feed.open_method" name="check" class="h-3 w-3 text-primary" />
        </button>

        <button
          @click="$emit('setOpenMethod', feed, 'app_browser')"
          class="rss-feed-menu__item rss-feed-menu__item--compact"
        >
          <AppIcon name="siteFallback" class="h-3.5 w-3.5 opacity-70" />
          <span class="flex-1">应用内浏览器</span>
          <AppIcon v-if="feed.open_method === 'app_browser'" name="check" class="h-3 w-3 text-primary" />
        </button>

        <button
          @click="$emit('setOpenMethod', feed, 'external_browser')"
          class="rss-feed-menu__item rss-feed-menu__item--compact"
        >
          <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
          <span class="flex-1">系统浏览器</span>
          <AppIcon v-if="feed.open_method === 'external_browser'" name="check" class="h-3 w-3 text-primary" />
        </button>

        <div class="rss-feed-menu__separator"></div>

        <button
          @click="$emit('unsubscribe', feed)"
          class="rss-feed-menu__item rss-feed-menu__item--danger"
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
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { RssFeed } from '@/features/rss/composables/rssTypes'

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

<style scoped>
.rss-feed-menu {
  position: fixed;
  z-index: var(--z-toast, 80);
  width: 12.5rem;
  padding: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.36);
  border-radius: 0.625rem;
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
}

.rss-feed-menu__list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.rss-feed-menu__item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  min-height: 2rem;
  padding: 0 0.625rem;
  border-radius: 0.5rem;
  color: hsl(var(--foreground));
  font-size: 0.75rem;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition:
    color 0.16s ease,
    background-color 0.16s ease;
}

.rss-feed-menu__item:hover,
.rss-feed-menu__item:focus-visible {
  background: hsl(var(--accent));
}

.rss-feed-menu__item--compact {
  min-height: 1.75rem;
}

.rss-feed-menu__item--danger {
  color: hsl(var(--destructive));
}

.rss-feed-menu__separator {
  height: 1px;
  margin: 0.25rem 0;
  background: hsl(var(--border) / 0.22);
}

.rss-feed-menu__label {
  padding: 0.25rem 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
}

@media (prefers-reduced-motion: reduce) {
  .rss-feed-menu__item {
    transition: none;
  }
}
</style>
