<template>
  <Teleport to="body">
    <div
      v-if="visible && entry"
      ref="rootRef"
      role="menu"
      aria-label="文章操作"
      class="rss-context-menu"
      :style="{ left: position.x + 'px', top: position.y + 'px' }"
    >
      <div class="rss-context-menu__list">
        <button
          role="menuitem"
          @click="$emit('toggleRead', entry)"
          class="rss-context-menu__item"
        >
          <AppIcon :name="entry.is_read ? 'eyeOff' : 'eye'" class="h-3.5 w-3.5 opacity-70" />
          <span>{{ entry.is_read ? '标记为未读' : '标记为已读' }}</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('toggleStar', entry)"
          class="rss-context-menu__item"
        >
          <AppIcon name="star" class="h-3.5 w-3.5 opacity-70" :class="entry.is_starred ? 'text-warning fill-amber-500' : ''" />
          <span>{{ entry.is_starred ? '取消收藏' : '收藏文章' }}</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('goToFeed', entry)"
          class="rss-context-menu__item"
        >
          <AppIcon name="inbox" class="h-3.5 w-3.5 opacity-70" />
          <span>查看订阅源</span>
        </button>

        <div class="rss-context-menu__separator" role="separator"></div>

        <template v-if="feed">
          <div class="rss-context-menu__label" role="group" aria-label="默认打开方式">默认打开方式</div>

          <button
            role="menuitemradio"
            :aria-checked="!feed.open_method"
            @click="$emit('setOpenMethod', feed, null)"
            class="rss-context-menu__item rss-context-menu__item--compact"
          >
            <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">内嵌阅读</span>
            <AppIcon v-if="!feed.open_method" name="check" class="h-3 w-3 text-primary" />
          </button>

          <button
            role="menuitemradio"
            :aria-checked="feed.open_method === 'app_browser'"
            @click="$emit('setOpenMethod', feed, 'app_browser')"
            class="rss-context-menu__item rss-context-menu__item--compact"
          >
            <AppIcon name="siteFallback" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">应用内浏览器</span>
            <AppIcon v-if="feed.open_method === 'app_browser'" name="check" class="h-3 w-3 text-primary" />
          </button>

          <button
            role="menuitemradio"
            :aria-checked="feed.open_method === 'external_browser'"
            @click="$emit('setOpenMethod', feed, 'external_browser')"
            class="rss-context-menu__item rss-context-menu__item--compact"
          >
            <AppIcon name="externalLink" class="h-3.5 w-3.5 opacity-70" />
            <span class="flex-1">系统浏览器</span>
            <AppIcon v-if="feed.open_method === 'external_browser'" name="check" class="h-3 w-3 text-primary" />
          </button>
        </template>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'above', true)"
          class="rss-context-menu__item"
        >
          <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
          <span>上方全部已读</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'below', true)"
          class="rss-context-menu__item"
        >
          <AppIcon name="eye" class="h-3.5 w-3.5 opacity-70" />
          <span>下方全部已读</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'all', true)"
          class="rss-context-menu__item"
        >
          <AppIcon name="list" class="h-3.5 w-3.5 opacity-70" />
          <span>列表全部已读</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('batchRead', 'all', false)"
          class="rss-context-menu__item"
        >
          <AppIcon name="eyeOff" class="h-3.5 w-3.5 opacity-70" />
          <span>列表全部未读</span>
        </button>

        <div class="rss-context-menu__separator" role="separator"></div>

        <button
          role="menuitem"
          @click="$emit('unsubscribe', entry)"
          class="rss-context-menu__item rss-context-menu__item--danger"
        >
          <AppIcon name="close" class="h-3.5 w-3.5 opacity-70" />
          <span>取消订阅该源</span>
        </button>

        <div class="rss-context-menu__separator" role="separator"></div>

        <button
          role="menuitem"
          @click="$emit('copyLink', entry)"
          class="rss-context-menu__item"
        >
          <AppIcon name="link" class="h-3.5 w-3.5 opacity-70" />
          <span>复制文章链接</span>
        </button>

        <button
          role="menuitem"
          @click="$emit('openExternal', entry)"
          class="rss-context-menu__item"
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

<style scoped>
.rss-context-menu {
  position: fixed;
  z-index: var(--z-toast, 80);
  width: 12.5rem;
  padding: 0.375rem;
  border: 1px solid hsl(var(--border) / 0.36);
  border-radius: 0.625rem;
  background: hsl(var(--popover));
  color: hsl(var(--popover-foreground));
}

.rss-context-menu__list {
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.rss-context-menu__item {
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

.rss-context-menu__item:hover,
.rss-context-menu__item:focus-visible {
  background: hsl(var(--accent));
}

.rss-context-menu__item--compact {
  min-height: 1.75rem;
}

.rss-context-menu__item--danger {
  color: hsl(var(--destructive));
}

.rss-context-menu__separator {
  height: 1px;
  margin: 0.25rem 0;
  background: hsl(var(--border) / 0.22);
}

.rss-context-menu__label {
  padding: 0.25rem 0.625rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 650;
}

@media (prefers-reduced-motion: reduce) {
  .rss-context-menu__item {
    transition: none;
  }
}
</style>
