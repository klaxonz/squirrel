<template>
  <div
    class="group flex cursor-pointer flex-col rounded-lg border border-border/50 bg-background p-3 transition-colors hover:bg-accent/40"
    @click="$emit('click')"
  >
    <div class="flex items-start gap-3">
      <div class="relative shrink-0">
        <div class="h-11 w-11 overflow-hidden rounded-md bg-muted">
          <SubscriptionAvatar
            :src="subscription.avatar"
            :name="subscription.name"
            size="full"
            class="h-full w-full object-cover"
          />
        </div>
        <div
          v-if="subscription.unread_count > 0"
          class="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-[10px] font-semibold text-primary-foreground ring-2 ring-background"
        >
          {{ subscription.unread_count > 99 ? '99+' : subscription.unread_count }}
        </div>
      </div>

      <div class="min-w-0 flex-1">
        <div class="flex items-start gap-2">
          <h3 class="line-clamp-2 flex-1 text-sm font-semibold leading-snug text-foreground">
            {{ subscription.name }}
          </h3>
          <button
            type="button"
            class="inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-md transition-colors"
            :class="subscription.is_special_followed ? 'text-amber-500' : 'text-muted-foreground/40 hover:bg-accent hover:text-foreground'"
            aria-label="切换特别关注"
            @click.stop="$emit('toggleSpecial', subscription)"
          >
            <AppIcon name="star" class="h-3.5 w-3.5" :class="{ 'fill-current': subscription.is_special_followed }" />
          </button>
          <div v-if="subscription.is_nsfw" class="shrink-0 rounded-md bg-destructive/10 px-1.5 py-0.5 text-[10px] font-medium text-destructive">
            敏感
          </div>
        </div>
        <div class="mt-1.5 flex items-center gap-2 text-xs text-muted-foreground">
          <SiteTag :site="subscription.site" class="origin-left scale-90" />
          <span>{{ subscription.total_videos || 0 }} 视频</span>
        </div>
      </div>
    </div>

    <div v-if="subscription.latest_videos?.length" class="mt-3">
      <div class="grid grid-cols-3 gap-1.5">
        <div
          v-for="video in subscription.latest_videos.slice(0, 3)"
          :key="video.id"
          class="aspect-video overflow-hidden rounded-md bg-muted"
        >
          <img
            v-if="video.thumbnail"
            :src="video.thumbnail"
            class="h-full w-full object-contain"
            loading="lazy"
          />
        </div>
        <div v-for="i in Math.max(0, 3 - (subscription.latest_videos?.length || 0))" :key="`p-${i}`" class="aspect-video rounded-md bg-muted/50" />
      </div>
    </div>

    <div class="mt-3 flex items-center justify-between border-t border-border/50 pt-2 text-xs text-muted-foreground">
      <div class="flex items-center gap-1.5">
        <AppIcon name="time" class="h-3.5 w-3.5" />
        <span>{{ lastUpdatedText }}</span>
      </div>
      
      <Button
        variant="ghost"
        size="icon"
        class="h-7 w-7 rounded-md opacity-0 transition-opacity group-hover:opacity-100"
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
