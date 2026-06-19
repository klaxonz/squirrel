<template>
  <div
    class="group flex cursor-pointer"
    :class="[layout === 'list' ? 'flex-row gap-4' : 'flex-col gap-2.5']"
    role="button"
    tabindex="0"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
    @keydown.enter.prevent="handleClick"
    @keydown.space.prevent="handleClick"
  >
    <!-- Thumbnail Container -->
    <div :class="[
      'relative overflow-hidden bg-muted transition-all duration-300 group-hover:brightness-110 group-hover:shadow-lg',
      layout === 'list' ? 'w-48 shrink-0 md:w-64 aspect-video' : 'aspect-video w-full'
    ]"
    :style="{ borderRadius: 'var(--app-card-radius)' }">
      <VideoThumbnail
        :src="thumbnailSrc"
        :alt="video.title"
        fit="responsive"
        interactive
        :blur="shouldBlurThumbnail"
      />

      <!-- Quick Actions (Hover) -->
      <div class="absolute top-1.5 right-1.5 flex flex-col gap-1.5 opacity-0 translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all duration-200 z-10">
        <button
          class="flex size-7 items-center justify-center rounded-md bg-black/60 text-white backdrop-blur hover:bg-primary hover:text-primary-foreground transition-colors"
          title="标记已读"
          @click.stop="toggleReadStatus(!isRead)"
        >
          <AppIcon :name="isRead ? 'statusSuccess' : 'check'" class="size-4" />
        </button>
        <button
          class="flex size-7 items-center justify-center rounded-md bg-black/60 text-white backdrop-blur hover:bg-primary hover:text-primary-foreground transition-colors"
          title="稍后再看"
          @click.stop="toggleLater"
        >
          <AppIcon :name="isLater === 1 ? 'watchLaterActive' : 'watchLater'" class="size-4" />
        </button>
        <button
          class="flex size-7 items-center justify-center rounded-md bg-black/60 backdrop-blur transition-colors"
          :class="isLiked === 1 ? 'text-red-500 bg-black/80 hover:bg-black/90' : 'text-white hover:bg-primary hover:text-primary-foreground'"
          title="喜欢"
          @click.stop="toggleLikeVideo"
        >
          <AppIcon name="heart" class="size-4" :class="{ 'fill-current': isLiked === 1 }" />
        </button>
      </div>

      <!-- Overlays -->
      <span v-if="video.duration" class="absolute bottom-1.5 right-1.5 inline-flex h-5 items-center rounded-md bg-black/65 px-1.5 text-[10px] font-medium tabular-nums text-white backdrop-blur-sm transition-opacity group-hover:opacity-0">
        {{ formatDuration(video.duration) }}
      </span>

      <!-- Bottom Shadow/Gradient for Overlay Visibility -->
      <div class="absolute bottom-0 inset-x-0 h-10 bg-gradient-to-t from-black/60 to-transparent opacity-100 pointer-events-none z-10" />

      <!-- Progress Bar -->
      <div v-if="progressRatio > 0" class="absolute bottom-0 inset-x-0 h-1 group-hover:h-1.5 transition-all duration-300 z-20 bg-white/30">
        <div class="h-full bg-white transition-all duration-500 ease-out" :style="{ width: `${progressRatio * 100}%` }" />
      </div>
    </div>

    <!-- Info Container -->
    <div :class="[
      'flex gap-3 px-0.5',
      layout === 'list' ? 'flex-1 py-1 min-w-0' : ''
    ]">
      <div v-if="showAvatar && displayAvatars.length && layout === 'grid'" class="shrink-0 mt-0.5">
        <SubscriptionAvatar
          :src="displayAvatars[0].avatar"
          :name="displayAvatars[0].name"
          size="lg"
          @click.stop="goToSubscription(displayAvatars[0].id)"
        />
      </div>

      <div class="flex-1 min-w-0 flex flex-col gap-1 justify-center"
           :class="{ 'min-h-[2.6em]': layout === 'grid' }">
        <h3 :class="[
          'font-semibold leading-[1.3] text-foreground/90 group-hover:text-primary transition-colors tracking-tight',
          layout === 'list' ? 'text-[16px] line-clamp-2 md:line-clamp-3 mb-1' : 'text-[14px] line-clamp-2'
        ]">
          {{ video.title }}
        </h3>

        <div class="flex flex-col gap-0.5">
          <div class="flex items-center gap-1.5 text-[12px] text-muted-foreground/80 font-medium">
            <div v-if="layout === 'list' && showAvatar && displayAvatars.length" class="shrink-0 mr-1">
              <SubscriptionAvatar
                :src="displayAvatars[0].avatar"
                :name="displayAvatars[0].name"
                size="xs"
                @click.stop="goToSubscription(displayAvatars[0].id)"
              />
            </div>
            <span class="hover:text-foreground transition-colors truncate" @click.stop="goToSubscription(primarySubscriptionId)">
              {{ displayNames }}
            </span>
            <span v-if="video.site" class="shrink-0 px-1 py-px rounded-[4px] bg-accent/50 text-[10px] font-bold text-muted-foreground uppercase tracking-wider">{{ video.site }}</span>
          </div>
          <div class="flex items-center gap-1 text-[11px] text-muted-foreground/70 font-medium">
            <span>{{ displayDateText }}</span>
            <span v-if="layout === 'list' && video.duration" class="ml-2 font-mono bg-muted px-1 rounded">{{ formatDuration(video.duration) }}</span>
          </div>
          <div v-if="layout === 'list' && video.description" class="hidden md:block mt-2 text-[12px] text-muted-foreground/70 line-clamp-2">
            {{ video.description }}
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

const props = defineProps<{
  video: VideoListItem
  showAvatar?: boolean
  sortBy?: string
  layout?: 'grid' | 'list'
}>()

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
  if (isLiked.value === 1) {
    const { error } = await deleteInteraction(props.video.id)
    if (!error) isLiked.value = null
  } else {
    const { error } = await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
    if (!error) isLiked.value = 1
  }
  showMenu.value = false
}

const toggleLater = async () => {
  if (isLater.value === 1) {
    const { error } = await deleteInteraction(props.video.id)
    if (!error) isLater.value = null
  } else {
    const { error } = await toggleLike(props.video.id, INTERACTION_TYPE.LATER)
    if (!error) isLater.value = 1
  }
}

onMounted(() => document.addEventListener('closeAllContextMenus', closeMenuOnExternalClose))
onUnmounted(() => document.removeEventListener('closeAllContextMenus', closeMenuOnExternalClose))
</script>

<style scoped>
</style>
