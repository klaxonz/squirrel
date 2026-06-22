<template>
  <div
    class="group flex cursor-pointer flex-col overflow-hidden rounded-lg border border-border/55 bg-card transition-[border-color,background-color,box-shadow] duration-200 hover:border-primary/40 hover:bg-accent/25"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-3 p-4 pb-2.5">
      <div class="relative shrink-0">
        <div class="h-14 w-14 overflow-hidden rounded-md bg-muted ring-1 ring-border/50 group-hover:ring-primary/30 transition-colors">
          <SubscriptionAvatar
            :src="subscription.avatar"
            :name="subscription.name"
            size="full"
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
        </div>
        <div
          v-if="subscription.unread_count > 0"
          class="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1 text-2xs font-semibold text-primary-foreground ring-2 ring-card shadow-[0_0_0_1px_hsl(var(--primary)/0.4)] app-mono"
        >
          {{ subscription.unread_count > 99 ? '99+' : subscription.unread_count }}
        </div>
      </div>

      <div class="min-w-0 flex-1 pt-0.5">
        <div class="flex items-start justify-between gap-2">
          <h3 class="app-h3 line-clamp-2 group-hover:text-primary transition-colors">
            {{ subscription.name }}
          </h3>
          <button
            type="button"
            class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-md transition-colors"
            :class="subscription.is_special_followed ? 'text-warning hover:bg-warning/10' : 'text-muted-foreground/40 hover:bg-accent/40 hover:text-foreground'"
            aria-label="切换特别关注"
            @click.stop="$emit('toggleSpecial', subscription)"
          >
            <AppIcon name="star" class="h-4 w-4" :class="{ 'fill-current': subscription.is_special_followed }" />
          </button>
        </div>
        <div class="mt-1.5 flex items-center gap-2">
          <SiteTag :site="subscription.site" class="origin-left scale-[0.85] opacity-90" />
          <span class="text-xs font-medium text-muted-foreground app-mono">{{ subscription.total_videos || 0 }} 视频</span>
          <div v-if="subscription.is_nsfw" class="shrink-0 rounded border border-destructive/30 bg-destructive/10 px-1.5 py-0.5 text-2xs font-semibold text-destructive ml-auto">
            18+
          </div>
        </div>
      </div>
    </div>

    <div v-if="subscription.latest_videos?.length" class="px-4 mt-1 mb-1.5">
      <div class="grid grid-cols-3 gap-1.5">
        <div
          v-for="video in subscription.latest_videos.slice(0, 3)"
          :key="video.id"
          class="aspect-video overflow-hidden rounded bg-muted/80 ring-1 ring-border/40 relative group/video"
        >
          <VideoThumbnail
            v-if="video.thumbnail"
            :src="video.thumbnail"
            fit="cover"
            img-class="transition-transform duration-300 group-hover/video:scale-105"
          />
          <div class="absolute inset-0 bg-black/30 opacity-0 group-hover/video:opacity-100 transition-opacity flex items-center justify-center">
            <AppIcon name="play" class="h-4 w-4 text-white" />
          </div>
        </div>
        <div v-for="i in Math.max(0, 3 - (subscription.latest_videos?.length || 0))" :key="`p-${i}`" class="aspect-video rounded bg-muted/30 border border-border/30 border-dashed" />
      </div>
    </div>

    <div class="mt-auto px-4 py-2.5 flex items-center justify-between border-t border-border/40">
      <div class="flex items-center gap-1.5 text-xs text-muted-foreground/80">
        <AppIcon name="time" class="h-3.5 w-3.5 opacity-70" />
        <span>{{ lastUpdatedText }}</span>
      </div>

      <Button
        variant="ghost"
        size="icon"
        class="h-7 w-7 rounded-md opacity-0 transition-opacity group-hover:opacity-100 hover:bg-accent/50"
        @click.stop="$emit('more')"
      >
        <AppIcon name="more" class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import SiteTag from '@/features/video/components/SiteTag.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { formatDate } from '@/shared/lib/dateFormat'
import type { SubscriptionListItem } from '@/features/video/types/subscription'

const props = defineProps<{
  subscription: SubscriptionListItem
}>()

defineEmits(['click', 'more', 'toggleSpecial'])

const lastUpdatedText = computed(() => {
  const date = props.subscription.updated_at || props.subscription.last_published_at
  return date ? formatDate(date) : '未知'
})
</script>
