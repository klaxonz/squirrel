<template>
  <AppContextMenu
    v-if="entry"
    :ref="bindRootRef"
    :visible="visible"
    label="文章操作"
    :position="position"
    @close="$emit('close')"
  >
    <AppContextMenuItem :icon="entry.is_read ? 'eyeOff' : 'eye'" @click="$emit('toggleRead', entry)">
      {{ entry.is_read ? '标记为未读' : '标记为已读' }}
    </AppContextMenuItem>

    <AppContextMenuItem icon="star" @click="$emit('toggleStar', entry)">
      {{ entry.is_starred ? '取消收藏' : '收藏文章' }}
    </AppContextMenuItem>

    <AppContextMenuItem icon="inbox" @click="$emit('goToFeed', entry)">
      查看订阅源
    </AppContextMenuItem>

    <AppContextMenuSeparator />

    <template v-if="feed">
      <AppContextMenuLabel aria-label="默认打开方式">默认打开方式</AppContextMenuLabel>

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
    </template>

    <AppContextMenuItem icon="eye" @click="$emit('batchRead', 'above', true)">
      上方全部已读
    </AppContextMenuItem>

    <AppContextMenuItem icon="eye" @click="$emit('batchRead', 'below', true)">
      下方全部已读
    </AppContextMenuItem>

    <AppContextMenuItem icon="list" @click="$emit('batchRead', 'all', true)">
      列表全部已读
    </AppContextMenuItem>

    <AppContextMenuItem icon="eyeOff" @click="$emit('batchRead', 'all', false)">
      列表全部未读
    </AppContextMenuItem>

    <AppContextMenuSeparator />

    <AppContextMenuItem icon="close" danger @click="$emit('unsubscribe', entry)">
      取消订阅该源
    </AppContextMenuItem>

    <AppContextMenuSeparator />

    <AppContextMenuItem icon="link" @click="$emit('copyLink', entry)">
      复制文章链接
    </AppContextMenuItem>

    <AppContextMenuItem icon="externalLink" @click="$emit('openExternal', entry)">
      在外部浏览器打开
    </AppContextMenuItem>
  </AppContextMenu>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import AppContextMenu from '@/shared/components/layout/AppContextMenu.vue'
import AppContextMenuItem from '@/shared/components/layout/AppContextMenuItem.vue'
import AppContextMenuLabel from '@/shared/components/layout/AppContextMenuLabel.vue'
import AppContextMenuSeparator from '@/shared/components/layout/AppContextMenuSeparator.vue'
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
  close: []
}>()

// ponytail: expose the rendered menu div so useRssEntries can still measure it
// for overflow repositioning after the template moved into this child.
const rootRef = ref<HTMLElement | null>(null)
const bindRootRef = (instance: unknown) => {
  const exposed = instance && typeof instance === 'object'
    ? instance as { rootRef?: HTMLElement | null }
    : null
  rootRef.value = exposed?.rootRef ?? null
}
defineExpose({ rootRef })
</script>
