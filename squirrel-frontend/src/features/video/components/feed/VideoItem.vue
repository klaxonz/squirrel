<template>
  <div
    class="group flex cursor-pointer rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-ring/40 focus-visible:ring-offset-2 focus-visible:ring-offset-background transition-shadow"
    :class="layout === 'list' ? 'flex-row gap-4' : 'flex-col gap-2.5'"
    role="button"
    tabindex="0"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
    @keydown.enter.prevent="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <div :class="[
      'relative overflow-hidden bg-muted rounded-lg ring-1 ring-border/40 transition-all duration-300 group-hover:shadow-card-hover group-active:scale-[0.99]',
      layout === 'list' ? 'w-48 shrink-0 md:w-64 aspect-video' : 'aspect-video w-full'
    ]">
      <VideoThumbnail
        :src="thumbnailSrc"
        :alt="video.title"
        fit="responsive"
        interactive
        :blur="shouldBlurThumbnail"
      />

      <!-- Quick Actions (Hover) -->
      <div class="absolute top-1.5 right-1.5 z-10 opacity-0 translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200">
        <div class="flex items-center gap-0.5 rounded-full bg-black/60 p-0.5 backdrop-blur shadow-lg ring-1 ring-white/10">
          <button
            class="flex size-7 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/15 hover:text-white"
            title="标记已读"
            @click.stop="toggleReadStatus(!isRead)"
          >
            <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-[15px]" />
          </button>
          <button
            class="flex size-7 items-center justify-center rounded-full text-white/80 transition-colors hover:bg-white/15 hover:text-white"
            title="稍后再看"
            @click.stop="toggleLater"
          >
            <AppIcon :name="isLater === 1 ? 'watchLaterActive' : 'watchLater'" class="size-[15px]" />
          </button>
          <button
            class="flex size-7 items-center justify-center rounded-full transition-colors"
            :class="isLiked === 1 ? 'text-red-400 hover:bg-white/10' : 'text-white/80 hover:bg-white/15 hover:text-white'"
            title="喜欢"
            @click.stop="toggleLikeVideo"
          >
            <AppIcon name="heart" class="size-[15px]" :class="{ 'fill-current': isLiked === 1 }" />
          </button>
        </div>
      </div>

      <span v-if="video.duration && showDuration" class="video-duration-badge absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/70 px-1.5 text-2xs font-medium text-white tabular-nums shadow-sm backdrop-blur-sm transition-opacity group-hover:opacity-0">
        {{ formatDuration(video.duration) }}
      </span>

      <!-- Bottom Shadow/Gradient for Overlay Visibility -->
      <div class="absolute bottom-0 inset-x-0 h-10 bg-gradient-to-t from-black/60 to-transparent opacity-100 pointer-events-none z-10" />

      <div v-if="progressRatio > 0" class="absolute bottom-0 inset-x-0 h-px group-hover:h-[2px] transition-all duration-300 z-20 bg-white/15">
        <div class="h-full bg-primary transition-[width] duration-500 ease-out" :style="{ width: `${progressRatio * 100}%` }" />
      </div>
    </div>

    <!-- Info Container -->
    <div :class="[
      'flex flex-col gap-1 px-0.5',
      layout === 'list' ? 'flex-1 py-1 min-w-0' : ''
    ]">
      <h3 :class="[
        'font-semibold leading-[1.3] text-foreground/90 group-hover:text-primary transition-colors tracking-tight',
        layout === 'list' ? 'text-base line-clamp-2 md:line-clamp-3 mb-0.5' : 'text-sm line-clamp-2'
      ]">
        {{ video.title }}
      </h3>

      <div class="flex items-start gap-3 min-w-0">
        <div v-if="showAvatar && displayAvatars.length" class="shrink-0 mt-0.5">
          <SubscriptionAvatar
            :src="displayAvatars[0].avatar"
            :name="displayAvatars[0].name"
            size="lg"
            @click.stop="goToSubscription(displayAvatars[0].id)"
          />
        </div>

        <div class="flex-1 min-w-0 flex flex-col gap-0.5">
          <div class="flex items-center gap-1.5 text-xs text-muted-foreground/80 font-medium">
            <span class="hover:text-foreground transition-colors truncate" @click.stop="goToSubscription(primarySubscriptionId)">
              {{ displayNames }}
            </span>
            <span v-if="video.site" class="shrink-0 px-1 py-px rounded bg-accent/50 text-2xs font-bold text-muted-foreground uppercase tracking-wider">{{ video.site }}</span>
          </div>
          <div class="flex items-center gap-1 text-xs text-muted-foreground/70 font-medium">
            <span>{{ displayDateText }}</span>
            <span v-if="layout === 'list' && video.duration" class="ml-2 font-mono bg-muted px-1 rounded">{{ formatDuration(video.duration) }}</span>
          </div>
        </div>
      </div>

      <div v-if="layout === 'list' && video.description" class="hidden md:block mt-1.5 text-xs text-muted-foreground/70 line-clamp-2">
        {{ video.description }}
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
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import SubscriptionAvatar from '@/features/video/components/SubscriptionAvatar.vue'
import ContextMenu from './ContextMenu.vue'
import VideoThumbnail from '@/features/video/components/feed/VideoThumbnail.vue'
import { useVideoHistory } from '@/features/video/composables/useVideoHistory'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { useSystemConfig } from '@/shared/composables/useSystemConfig'
import { formatDate, formatDuration } from '@/shared/lib/dateFormat'
import type { VideoListItem } from '@/features/video/types/video'

const props = withDefaults(defineProps<{
  video: VideoListItem
  showAvatar?: boolean
  sortBy?: string
  layout?: 'grid' | 'list'
  showDuration?: boolean
}>(), {
  layout: 'grid',
  showDuration: true,
})

const emit = defineEmits(['goToSubscription', 'openModal'])

const { config: systemConfig } = useSystemConfig()
const { clearHistory, sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })

// ponytail: read/like/later interaction state. The list endpoint does not
// return these flags, so they are kept as local optimistic UI state here
// rather than mutated on the props object (which would violate one-way flow
// and previously wrote to nonexistent fields).
const isRead = ref(false)
const isLiked = ref<number | null>(null)
const isLater = ref<number | null>(null)

const thumbnailSrc = computed(() => String(props.video?.thumbnail || '').trim())
const isNsfwVideo = computed(() => props.video.subscriptions?.some((s) => s.is_nsfw))
const shouldBlurThumbnail = computed(() => Boolean(systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value))

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
  const names = (props.video.subscriptions || props.video.actors || []).map((a) => a.name)
  return names.length ? names.join(' / ') : '未知'
})

const primarySubscriptionId = computed(() => props.video.subscriptions?.[0]?.id || props.video.actors?.[0]?.id)

const closeMenuOnExternalClose = () => { showMenu.value = false }

const showContextMenu = async (event: MouseEvent) => {
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))
  await nextTick()
  menuPosition.value = { x: event.clientX, y: event.clientY }
  showMenu.value = true
}

const handleClick = () => emit('openModal', props.video)
const goToSubscription = (id: number | string | null | undefined) => id && emit('goToSubscription', id)

const toggleReadStatus = async (markRead: boolean) => {
  if (markRead) {
    const pos = Number(props.video.duration || 0)
    await sendReport(props.video.id, pos, { force: true })
    isRead.value = true
  } else {
    await clearHistory([props.video.id])
    isRead.value = false
  }
  showMenu.value = false
}

const toggleLikeVideo = async () => {
  try {
    if (isLiked.value === 1) {
      await deleteInteraction(props.video.id)
      isLiked.value = null
    } else {
      await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
      isLiked.value = 1
    }
  } catch {
    // silent — toggle failure leaves the prior like state
  }
  showMenu.value = false
}

const toggleLater = async () => {
  try {
    if (isLater.value === 1) {
      await deleteInteraction(props.video.id)
      isLater.value = null
    } else {
      await toggleLike(props.video.id, INTERACTION_TYPE.LATER)
      isLater.value = 1
    }
  } catch {
    // silent — toggle failure leaves the prior later state
  }
}

onMounted(() => document.addEventListener('closeAllContextMenus', closeMenuOnExternalClose))
onUnmounted(() => document.removeEventListener('closeAllContextMenus', closeMenuOnExternalClose))
</script>
