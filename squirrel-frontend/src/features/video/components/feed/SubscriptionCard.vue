<template>
  <div
    class="group flex cursor-pointer flex-col overflow-hidden rounded-md border border-border/55 bg-card transition-[border-color,background-color,box-shadow] duration-200 hover:border-primary/40 hover:bg-accent/25"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-2.5 p-3 pb-2">
      <div class="relative shrink-0">
        <div class="h-11 w-11 overflow-hidden rounded-md bg-muted ring-1 ring-border/50 group-hover:ring-primary/30 transition-colors">
          <SubscriptionAvatar
            :src="subscription.avatar"
            :name="subscription.name"
            size="full"
            class="h-full w-full object-cover"
          />
        </div>
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex items-start justify-between gap-2">
          <h3 class="line-clamp-2 text-sm font-semibold leading-snug tracking-normal group-hover:text-primary transition-colors">
            {{ subscription.name }}
          </h3>
          <Button
            type="button"
            variant="ghost"
            size="mini-icon"
            class="shrink-0"
            :class="subscription.is_special_followed ? 'text-warning' : 'text-muted-foreground/40'"
            aria-label="切换特别关注"
            @click.stop="$emit('toggleSpecial', subscription)"
          >
            <AppIcon :name="subscription.is_special_followed ? 'bookmarkCheck' : 'bookmarkPlus'" class="h-4 w-4" />
          </Button>
        </div>
        <div class="mt-1 flex items-center gap-2">
          <SiteTag :site="subscription.site" class="origin-left scale-[0.85] opacity-90" />
          <span class="text-xs font-medium text-muted-foreground app-mono">{{ subscription.total_videos || 0 }} 视频</span>
          <div v-if="subscription.is_nsfw" class="app-badge-nsfw">
            18+
          </div>
        </div>
      </div>
    </div>

    <div v-if="subscription.latest_videos?.length" class="px-3 mt-1 mb-1.5">
      <div class="grid grid-cols-3 gap-1.5">
        <div
          v-for="video in subscription.latest_videos.slice(0, 3)"
          :key="video.id"
          class="video-preview-thumb relative aspect-video overflow-hidden rounded-md group/video"
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
        <div v-for="i in Math.max(0, 3 - (subscription.latest_videos?.length || 0))" :key="`p-${i}`" class="aspect-video rounded-md bg-black/25 border border-dashed border-white/10" />
      </div>
    </div>

    <div class="mt-auto px-3 py-2 flex items-center justify-between border-t border-border/40">
      <div class="flex items-center gap-1.5 text-xs text-muted-foreground/80">
        <AppIcon name="time" class="h-3.5 w-3.5 opacity-70" />
        <span>{{ lastUpdatedText }}</span>
      </div>

      <Button
        variant="ghost"
        size="icon-sm"
        class="opacity-0 transition-opacity group-hover:opacity-100"
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

<style scoped>
/* NSFW chip — destructive-tinted but with a higher-contrast foreground than
   raw `text-destructive on bg-destructive/10` which hovered below 3:1 in the
   dark theme. A light-on-color combo clears WCAG AA for ≥18pt / bold text. */
.app-badge-nsfw {
  margin-left: auto;
  flex-shrink: 0;
  padding: 0.125rem 0.5rem;
  font-size: 0.6875rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  color: hsl(0 0% 100%);
  background: hsl(var(--destructive));
  border-radius: var(--radius-sm);
}

/* Mini preview thumbs — no light ring (reads as white fringe). */
.video-preview-thumb {
  border: 0;
  background: hsl(0 0% 0% / 0.55);
  isolation: isolate;
}
</style>
