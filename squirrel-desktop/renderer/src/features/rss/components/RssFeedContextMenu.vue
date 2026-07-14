<template>
  <AppContextMenu
    v-if="feed"
    :ref="bindRootRef"
    :visible="visible"
    label="订阅源操作"
    :position="position"
    @close="$emit('close')"
  >
    <AppContextMenuItem icon="eye" @click="$emit('markAllRead', feed)">
      全部标记为已读
    </AppContextMenuItem>

    <AppContextMenuItem icon="refresh" @click="$emit('syncFeed', feed)">
      同步文章
    </AppContextMenuItem>

    <AppContextMenuItem icon="link" @click="$emit('copyLink', feed)">
      复制订阅源地址
    </AppContextMenuItem>

    <AppContextMenuItem v-if="feed.site_url" icon="externalLink" @click="$emit('openSite', feed)">
      访问源网站
    </AppContextMenuItem>

    <AppContextMenuSeparator />

    <AppContextMenuLabel>默认打开方式</AppContextMenuLabel>

    <AppContextMenuItem
      icon="list"
      role="menuitemradio"
      compact
      :checked="!feed.open_method"
      @click="$emit('setOpenMethod', feed, null)"
    >
      内嵌阅读
    </AppContextMenuItem>

    <AppContextMenuItem
      icon="siteFallback"
      role="menuitemradio"
      compact
      :checked="feed.open_method === 'app_browser'"
      @click="$emit('setOpenMethod', feed, 'app_browser')"
    >
      应用内浏览器
    </AppContextMenuItem>

    <AppContextMenuItem
      icon="externalLink"
      role="menuitemradio"
      compact
      :checked="feed.open_method === 'external_browser'"
      @click="$emit('setOpenMethod', feed, 'external_browser')"
    >
      系统浏览器
    </AppContextMenuItem>

    <AppContextMenuSeparator />

    <AppContextMenuItem icon="close" danger @click="$emit('unsubscribe', feed)">
      取消订阅
    </AppContextMenuItem>
  </AppContextMenu>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppContextMenu from '@/shared/components/layout/AppContextMenu.vue'
import AppContextMenuItem from '@/shared/components/layout/AppContextMenuItem.vue'
import AppContextMenuLabel from '@/shared/components/layout/AppContextMenuLabel.vue'
import AppContextMenuSeparator from '@/shared/components/layout/AppContextMenuSeparator.vue'
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
  close: []
}>()

// ponytail: expose the rendered menu div so the parent's composable
// (useRssFeeds) can still measure it for overflow repositioning after the
// template moved into this child component.
const rootRef = ref<HTMLElement | null>(null)
const bindRootRef = (instance: unknown) => {
  const exposed = instance && typeof instance === 'object'
    ? instance as { rootRef?: HTMLElement | null }
    : null
  rootRef.value = exposed?.rootRef ?? null
}
defineExpose({ rootRef })
</script>
