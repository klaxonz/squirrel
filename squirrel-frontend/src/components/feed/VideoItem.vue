<template>
  <div
    class="group flex flex-col gap-2.5 cursor-pointer"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <!-- Thumbnail Container -->
    <div class="relative aspect-video overflow-hidden rounded-lg bg-muted transition-colors group-hover:bg-muted/80">
      <img
        v-if="thumbnailSrc && !showThumbnailFallback"
        :src="thumbnailSrc"
        loading="lazy"
        decoding="async"
        referrerpolicy="no-referrer"
        class="h-full w-full object-contain transition-opacity duration-200"
        :class="[
          shouldBlurThumbnail ? 'blur-2xl scale-110' : '',
          imageLoaded ? 'opacity-100' : 'opacity-0'
        ]"
        :alt="video.title"
        @load="imageLoaded = true"
        @error="showThumbnailFallback = true"
      >

      <div v-else class="absolute inset-0 flex items-center justify-center bg-muted">
        <AppIcon name="imageOff" class="h-6 w-6 text-muted-foreground/20" />
      </div>

      <!-- Overlays -->
      <span v-if="video.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm">
        {{ formatDuration(video.duration) }}
      </span>

      <div v-if="progressRatio > 0" class="absolute bottom-0 left-0 right-0 h-0.5 overflow-hidden bg-black/20">
        <div class="h-full bg-primary transition-all duration-500" :style="{ width: `${progressRatio * 100}%` }" />
      </div>
    </div>

    <!-- Info Container -->
    <div class="flex gap-3 px-0.5">
      <div v-if="showAvatar && displayAvatars.length" class="shrink-0 mt-0.5">
        <SubscriptionAvatar
          :src="displayAvatars[0].avatar"
          :name="displayAvatars[0].name"
          size="sm"
          class="w-8 h-8 rounded-full ring-1 ring-border/20 shadow-sm transition-transform group-hover:scale-105"
          @click.stop="goToSubscription(displayAvatars[0].id)"
        />
      </div>
      
      <div class="flex-1 min-w-0 flex flex-col gap-1">
        <h3 class="text-[14px] font-semibold leading-[1.3] text-foreground/90 line-clamp-2 group-hover:text-primary transition-colors tracking-tight">
          {{ video.title }}
        </h3>
        
        <div class="flex flex-col">
          <div class="flex items-center gap-1.5 text-[12px] text-muted-foreground/80 font-medium">
            <span class="hover:text-foreground transition-colors truncate" @click.stop="goToSubscription(primarySubscriptionId)">
              {{ displayNames }}
            </span>
            <span v-if="video.site" class="shrink-0 px-1 py-0 rounded-[4px] bg-accent/50 text-[9px] font-bold text-muted-foreground uppercase tracking-wider">{{ video.site }}</span>
          </div>
          <div class="flex items-center gap-1 text-[11px] text-muted-foreground/50 font-medium">
            <span>{{ displayDateText }}</span>
          </div>
        </div>
      </div>
    </div>

    <Teleport to="body">
      <ContextMenu
        v-if="showMenu"
        :position="menuPosition"
        :is-open="showMenu"
        :video="video"
        @close="showMenu = false"
        @toggleReadStatus="toggleReadStatus"
        @toggleLike="toggleLikeVideo"
      />
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, toRef } from 'vue'
import AppIcon from '@/components/common/AppIcon.vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import ContextMenu from './ContextMenu.vue'
import useVideoHistory from '@/composables/useVideoHistory'
import useVideoInteraction from '@/composables/useVideoInteraction'
import { useSystemConfig } from '@/composables/useSystemConfig'
import { formatDate, formatDuration } from '@/utils/dateFormat'

const props = defineProps<{
  video: any
  showAvatar?: boolean
  sortBy?: string
}>()

const emit = defineEmits(['goToSubscription', 'openModal'])

const { config: systemConfig } = useSystemConfig()
const { clearHistory, sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()

const showMenu = ref(false)
const imageLoaded = ref(false)
const showThumbnailFallback = ref(false)
const menuPosition = ref({ x: 0, y: 0 })

const thumbnailSrc = computed(() => String(props.video?.thumbnail || '').trim())
const isNsfwVideo = computed(() => props.video.subscriptions?.some((s: any) => s.is_nsfw))
const shouldBlurThumbnail = computed(() => systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value)

const progressRatio = computed(() => {
  const d = Number(props.video?.duration || 0)
  return d > 0 ? Math.min(1, Number(props.video?.last_position || 0) / d) : 0
})

const displayDateText = computed(() => {
  const t = props.sortBy === 'created_at' ? (props.video.created_at || props.video.uploaded_at) : (props.video.uploaded_at || props.video.created_at)
  return t ? formatDate(t) : ''
})

const displayAvatars = computed(() => {
  const subs = props.video.subscriptions || []
  const actors = props.video.actors || []
  return (subs.length ? subs : actors).slice(0, 1)
})

const displayNames = computed(() => {
  const names = (props.video.subscriptions || props.video.actors || []).map((a: any) => a.name)
  return names.length ? names.join(' / ') : '未知'
})

const primarySubscriptionId = computed(() => props.video.subscriptions?.[0]?.id || props.video.actors?.[0]?.id)

const showContextMenu = async (event: MouseEvent) => {
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))
  await nextTick()
  menuPosition.value = { x: event.clientX, y: event.clientY }
  showMenu.value = true
}

const handleClick = () => emit('openModal', props.video)
const goToSubscription = (id: any) => id && emit('goToSubscription', id)

const toggleReadStatus = async (isRead: boolean) => {
  if (isRead) {
    const pos = Number(props.video.duration || 0)
    await sendReport(props.video.id, pos, { force: true })
    props.video.is_read = true
    props.video.last_position = pos
  } else {
    await clearHistory([props.video.id])
    props.video.is_read = false
    props.video.last_position = 0
  }
  showMenu.value = false
}

const toggleLikeVideo = async () => {
  if (props.video.is_liked === 1) {
    const { error } = await deleteInteraction(props.video.id)
    if (!error) props.video.is_liked = null
  } else {
    const { error } = await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
    if (!error) props.video.is_liked = 1
  }
  showMenu.value = false
}

onMounted(() => document.addEventListener('closeAllContextMenus', () => showMenu.value = false))
</script>

<style scoped>
.group:hover .group-hover\:premium-shadow {
  box-shadow: var(--shadow-premium);
}
</style>
