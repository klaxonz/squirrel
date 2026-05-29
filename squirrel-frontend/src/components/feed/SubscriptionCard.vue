<template>
  <div
    class="group flex cursor-pointer flex-col overflow-hidden rounded-2xl border border-border/40 bg-background/50 shadow-sm transition-all hover:-translate-y-1 hover:shadow-lg hover:border-primary/20 hover:bg-background backdrop-blur-sm"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-3 p-4 pb-2">
      <div class="relative shrink-0">
        <div class="h-14 w-14 overflow-hidden rounded-xl bg-muted ring-1 ring-border/50 group-hover:ring-primary/20 transition-all">
          <SubscriptionAvatar
            :src="subscription.avatar"
            :name="subscription.name"
            size="full"
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-110"
          />
        </div>
        <div
          v-if="subscription.unread_count > 0"
          class="absolute -right-1.5 -top-1.5 flex h-6 min-w-6 items-center justify-center rounded-full bg-primary px-1.5 text-[11px] font-bold text-primary-foreground ring-2 ring-background shadow-sm"
        >
          {{ subscription.unread_count > 99 ? '99+' : subscription.unread_count }}
        </div>
      </div>

      <div class="min-w-0 flex-1 pt-0.5">
        <div class="flex items-start justify-between gap-2">
          <h3 class="line-clamp-2 text-[15px] font-bold leading-tight text-foreground/90 group-hover:text-primary transition-colors">
            {{ subscription.name }}
          </h3>
          <button
            type="button"
            class="inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-lg transition-all"
            :class="subscription.is_special_followed ? 'text-amber-500 bg-amber-500/10 hover:bg-amber-500/20' : 'text-muted-foreground/30 hover:bg-accent hover:text-foreground'"
            aria-label="切换特别关注"
            @click.stop="$emit('toggleSpecial', subscription)"
          >
            <AppIcon name="star" class="h-4 w-4" :class="{ 'fill-current drop-shadow-sm': subscription.is_special_followed }" />
          </button>
        </div>
        <div class="mt-1.5 flex items-center gap-2">
          <SiteTag :site="subscription.site" class="origin-left scale-[0.85] opacity-80" />
          <span class="text-xs font-semibold text-muted-foreground bg-muted/60 px-1.5 py-0.5 rounded-md">{{ subscription.total_videos || 0 }} 视频</span>
          <div v-if="subscription.is_nsfw" class="shrink-0 rounded-md bg-destructive/10 px-1.5 py-0.5 text-[10px] font-bold text-destructive ml-auto">
            18+
          </div>
        </div>
      </div>
    </div>

    <div v-if="subscription.latest_videos?.length" class="px-4 mt-2 mb-1">
      <div class="grid grid-cols-3 gap-2">
        <div
          v-for="video in subscription.latest_videos.slice(0, 3)"
          :key="video.id"
          class="aspect-video overflow-hidden rounded-lg bg-muted/80 ring-1 ring-border/30 relative group/video"
        >
          <VideoThumbnail
            v-if="video.thumbnail"
            :src="video.thumbnail"
            fit="cover"
            img-class="transition-transform duration-300 group-hover/video:scale-105"
          />
          <div class="absolute inset-0 bg-black/20 opacity-0 group-hover/video:opacity-100 transition-opacity flex items-center justify-center">
            <AppIcon name="play" class="h-4 w-4 text-white" />
          </div>
        </div>
        <div v-for="i in Math.max(0, 3 - (subscription.latest_videos?.length || 0))" :key="`p-${i}`" class="aspect-video rounded-lg bg-muted/40 border border-border/20 border-dashed" />
      </div>
    </div>

    <div class="mt-auto px-4 py-3 flex items-center justify-between border-t border-border/5 bg-accent/20 group-hover:bg-accent/40 transition-colors">
      <div class="flex items-center gap-1.5 text-xs font-medium text-muted-foreground/80">
        <AppIcon name="time" class="h-3.5 w-3.5 opacity-70" />
        <span>{{ lastUpdatedText }}</span>
      </div>
      
      <Button
        variant="ghost"
        size="icon"
        class="h-7 w-7 rounded-lg opacity-0 transition-opacity group-hover:opacity-100 hover:bg-background"
        @click.stop="$emit('more')"
      >
        <AppIcon name="more" class="h-4 w-4" />
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import { Button } from '@/components/ui/button'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import SiteTag from '@/components/common/SiteTag.vue'
import VideoThumbnail from '@/components/feed/VideoThumbnail.vue'
import { formatDate } from '@/utils/dateFormat'

const props = defineProps<{
  subscription: any
}>()

defineEmits(['click', 'more', 'toggleSpecial'])

const lastUpdatedText = computed(() => {
  const date = props.subscription.updated_at || props.subscription.last_published_at
  return date ? formatDate(date) : '未知'
})
</script>
