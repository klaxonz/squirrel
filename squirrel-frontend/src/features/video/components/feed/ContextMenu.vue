<template>
  <AppContextMenu
    :visible="isOpen"
    label="视频操作"
    width="11.5rem"
    :position="position"
    @close="$emit('close')"
  >
    <AppContextMenuItem icon="check" @click="handleToggleRead(true)">
      标记为已读
    </AppContextMenuItem>

    <AppContextMenuItem icon="close" @click="handleToggleRead(false)">
      标记为未读
    </AppContextMenuItem>

    <AppContextMenuSeparator />

    <AppContextMenuItem :icon="likeIcon" :danger="isLiked === 1" @click="handleLiked">
      {{ likeLabel }}
    </AppContextMenuItem>

    <AppContextMenuItem icon="clipboard" @click="handleCopyVideoLink">
      复制链接
    </AppContextMenuItem>
  </AppContextMenu>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppContextMenu from '@/shared/components/layout/AppContextMenu.vue'
import AppContextMenuItem from '@/shared/components/layout/AppContextMenuItem.vue'
import AppContextMenuSeparator from '@/shared/components/layout/AppContextMenuSeparator.vue'
import type { AppIconName } from '@/shared/icons/app-icons'
import type { VideoListItem } from '@/features/video/types/video'

const props = defineProps<{
  position: { x: number; y: number }
  isOpen: boolean
  video: VideoListItem
  isLiked: number | null
}>()

const emit = defineEmits<{
  close: []
  toggleReadStatus: [isRead: boolean]
  copyVideoLink: []
  toggleLike: [video: VideoListItem]
}>()

const likeIcon = computed<AppIconName>(() => {
  if (props.isLiked === 0) return 'dislike'
  return 'heart'
})

const likeLabel = computed(() => {
  if (props.isLiked === 1) return '已喜欢'
  if (props.isLiked === 0) return '不喜欢'
  return '喜欢'
})

const handleToggleRead = (isRead: boolean) => {
  emit('toggleReadStatus', isRead)
}

const handleCopyVideoLink = async () => {
  emit('copyVideoLink')
  emit('close')
}

const handleLiked = async () => {
  emit('toggleLike', props.video)
  emit('close')
}

</script>
