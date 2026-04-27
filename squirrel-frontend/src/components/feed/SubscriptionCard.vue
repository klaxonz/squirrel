<template>
  <div
    class="group relative flex flex-col p-5 rounded-[24px] bg-card hover:bg-accent/30 border border-border/40 transition-all duration-500 cursor-pointer shadow-sm hover:shadow-2xl hover:-translate-y-1 overflow-hidden"
    @click="$emit('click')"
  >
    <!-- Background Glass Effect -->
    <div class="absolute -top-12 -right-12 w-32 h-32 bg-primary/5 blur-3xl rounded-full group-hover:bg-primary/10 transition-colors duration-700" />

    <div class="relative flex items-center gap-5 mb-5">
      <!-- Avatar Section -->
      <div class="relative shrink-0">
        <div class="w-16 h-16 rounded-2xl overflow-hidden ring-1 ring-border/20 shadow-md transition-all duration-500 group-hover:scale-105 group-hover:ring-primary/20">
          <SubscriptionAvatar
            :src="subscription.avatar"
            :name="subscription.name"
            size="full"
            class="w-full h-full object-cover transition-transform duration-700 group-hover:scale-110"
          />
        </div>
        <!-- Unread Indicator (Badge) -->
        <div
          v-if="subscription.unread_count > 0"
          class="absolute -top-2 -right-2 min-w-[22px] h-[22px] px-1.5 flex items-center justify-center bg-primary text-[10px] font-black text-primary-foreground rounded-full border-[3px] border-card shadow-lg"
        >
          {{ subscription.unread_count > 99 ? '99+' : subscription.unread_count }}
        </div>
      </div>

      <!-- Info Section -->
      <div class="flex-1 min-w-0">
        <div class="flex flex-col gap-1">
          <div class="flex items-center justify-between">
            <SiteTag :site="subscription.site" class="scale-90 origin-left" />
            <div v-if="subscription.is_nsfw" class="px-1.5 py-0.5 rounded-md bg-destructive/10 text-destructive text-[8px] font-black uppercase tracking-wider border border-destructive/20">
              NSFW
            </div>
          </div>
          <h3 class="font-bold text-[15px] leading-tight text-foreground line-clamp-2 group-hover:text-primary transition-colors tracking-tight">
            {{ subscription.name }}
          </h3>
        </div>
      </div>
    </div>

    <!-- Latest Videos Row (YouTube Style) -->
    <div v-if="subscription.latest_videos?.length" class="mt-auto flex flex-col gap-3">
      <div class="flex items-center justify-between">
        <span class="text-[10px] font-black text-muted-foreground/40 uppercase tracking-widest">最近发布</span>
        <div class="flex items-center gap-1.5 text-[10px] font-bold text-muted-foreground/30">
          <AppIcon name="time" class="w-2.5 h-2.5" />
          <span>{{ lastUpdatedText }}</span>
        </div>
      </div>
      
      <div class="grid grid-cols-3 gap-2">
        <div
          v-for="video in subscription.latest_videos.slice(0, 3)"
          :key="video.id"
          class="aspect-video rounded-lg bg-accent/20 overflow-hidden ring-1 ring-border/10 relative group/thumb"
        >
          <img
            v-if="video.thumbnail"
            :src="video.thumbnail"
            class="w-full h-full object-cover transition-transform duration-500 group-hover/thumb:scale-110"
            loading="lazy"
          />
          <div class="absolute inset-0 bg-black/20 opacity-0 group-hover/thumb:opacity-100 transition-opacity" />
        </div>
        <!-- Placeholders -->
        <div v-for="i in Math.max(0, 3 - (subscription.latest_videos?.length || 0))" :key="`p-${i}`" class="aspect-video rounded-lg bg-accent/5 border border-dashed border-border/20" />
      </div>
    </div>

    <!-- Stats Footer -->
    <div class="mt-4 pt-4 border-t border-border/10 flex items-center justify-between opacity-40 group-hover:opacity-100 transition-opacity duration-500">
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider">
          <AppIcon name="library" class="w-3.5 h-3.5" />
          <span>{{ subscription.total_videos }} 视频</span>
        </div>
      </div>
      
      <Button
        variant="ghost"
        size="icon"
        class="h-7 w-7 rounded-lg hover:bg-accent/50"
        @click.stop="$emit('more')"
      >
        <AppIcon name="more" class="w-4 h-4" />
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

defineEmits(['click', 'more'])

const lastUpdatedText = computed(() => {
  const date = props.subscription.updated_at || props.subscription.last_published_at
  return date ? formatDate(date) : '未知'
})
</script>
