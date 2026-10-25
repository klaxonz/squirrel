<template>
  <div v-if="inline" class="video-item__inline-actions">
    <Button
      variant="ghost"
      size="sm" icon-only
      class="video-item__inline-btn"
      :class="{ 'is-on': isLiked }"
      :title="isLiked ? '取消喜欢' : '喜欢'"
      :aria-pressed="isLiked"
      data-action="like"
      @click.stop="emit('toggleLike')"
    >
      <AppIcon name="heart" class="size-4" :class="{ 'fill-current': isLiked }" />
    </Button>
    <Button
      variant="ghost"
      size="sm" icon-only
      class="video-item__inline-btn"
      :class="{ 'is-on': isRead }"
      :title="isRead ? '标记未读' : '标记已读'"
      :aria-pressed="isRead"
      data-action="read"
      @click.stop="emit('toggleRead', !isRead)"
    >
      <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-4" />
    </Button>
    <Button
      variant="ghost"
      size="sm" icon-only
      class="video-item__inline-btn"
      :class="{ 'is-on': isLater }"
      :title="isLater ? '取消稍后看' : '稍后看'"
      :aria-pressed="isLater"
      data-action="later"
      @click.stop="emit('toggleLater')"
    >
      <AppIcon :name="isLater ? 'watchLaterActive' : 'watchLater'" class="size-4" />
    </Button>
  </div>
  <div v-else-if="overlay" class="video-item__overlay-actions">
    <Button
      variant="secondary"
      size="sm" icon-only
      class="video-item__overlay-btn"
      :class="{ 'is-on': isLiked }"
      :title="isLiked ? '取消喜欢' : '喜欢'"
      :aria-pressed="isLiked"
      data-action="like"
      @click.stop="emit('toggleLike')"
    >
      <AppIcon name="heart" class="size-4" :class="{ 'fill-current': isLiked }" />
    </Button>
    <Button
      variant="secondary"
      size="sm" icon-only
      class="video-item__overlay-btn"
      :class="{ 'is-on': isRead }"
      :title="isRead ? '标记未读' : '标记已读'"
      :aria-pressed="isRead"
      data-action="read"
      @click.stop="emit('toggleRead', !isRead)"
    >
      <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-4" />
    </Button>
    <Button
      variant="secondary"
      size="sm" icon-only
      class="video-item__overlay-btn"
      :class="{ 'is-on': isLater }"
      :title="isLater ? '取消稍后看' : '稍后看'"
      :aria-pressed="isLater"
      data-action="later"
      @click.stop="emit('toggleLater')"
    >
      <AppIcon :name="isLater ? 'watchLaterActive' : 'watchLater'" class="size-4" />
    </Button>
  </div>
  <footer v-else class="video-item__bar">
    <Button variant="ghost" size="sm" class="video-item__bar-btn" :class="{ 'is-on': isLiked }"
      :title="isLiked ? '取消喜欢' : '喜欢'" :aria-pressed="isLiked" data-action="like"
      @click="emit('toggleLike')">
      <AppIcon name="heart" class="size-4" :class="{ 'fill-current': isLiked }" />
      <span>{{ isLiked ? '已喜欢' : '喜欢' }}</span>
    </Button>
    <Button variant="ghost" size="sm" class="video-item__bar-btn" :class="{ 'is-on': isRead }"
      :title="isRead ? '标记未读' : '标记已读'" :aria-pressed="isRead" data-action="read"
      @click="emit('toggleRead', !isRead)">
      <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-4" />
      <span>{{ isRead ? '已读' : '标已读' }}</span>
    </Button>
    <Button variant="ghost" size="sm" class="video-item__bar-btn" :class="{ 'is-on': isLater }"
      :title="isLater ? '取消稍后看' : '稍后看'" :aria-pressed="isLater" data-action="later"
      @click="emit('toggleLater')">
      <AppIcon :name="isLater ? 'watchLaterActive' : 'watchLater'" class="size-4" />
      <span>稍后看</span>
    </Button>
  </footer>
</template>

<script setup lang="ts">
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'

withDefaults(defineProps<{
  isLiked: boolean
  isRead: boolean
  isLater: boolean
  overlay?: boolean
  inline?: boolean
}>(), { overlay: false, inline: false })

const emit = defineEmits<{
  toggleLike: []
  toggleRead: [markRead: boolean]
  toggleLater: []
}>()
</script>
