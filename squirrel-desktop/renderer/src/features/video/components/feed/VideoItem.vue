<template>
  <article
    class="video-item group"
    :class="[
      layout === 'list'
        ? (appearance === 'workbench' ? 'video-item--row' : 'video-item--card')
        : 'video-item--grid',
      `video-item--appearance-${appearance}`,
    ]"
    @contextmenu.prevent="showContextMenu"
    @pointerenter="prefetchPlayback"
    @pointerdown.left="prefetchPlayback"
  >
    <VideoItemWorkbenchLayout
      v-if="layout === 'list' && appearance === 'workbench'"
      :video="video"
      :thumbnail="thumbnailPresentation"
      :profile="profilePresentation"
      :actions="actionPresentation"
      @activate="handleOpen"
      @open-profile="goToProfile"
      @toggle-like="toggleLikeVideo"
      @toggle-read="toggleReadStatus"
      @toggle-later="toggleLater"
    />
    <VideoItemFeedLayout
      v-else-if="layout === 'list'"
      :video="video"
      :thumbnail="thumbnailPresentation"
      :profile="profilePresentation"
      :actions="actionPresentation"
      @activate="handleOpen"
      @open-profile="goToProfile"
      @toggle-like="toggleLikeVideo"
      @toggle-read="toggleReadStatus"
      @toggle-later="toggleLater"
    />
    <VideoItemGridLayout
      v-else
      :video="video"
      :thumbnail="thumbnailPresentation"
      :profile="profilePresentation"
      @activate="handleOpen"
      @open-profile="goToProfile"
    />

    <Teleport to="body">
      <ContextMenu
        v-if="showMenu"
        :position="menuPosition"
        :is-open="showMenu"
        :video="video"
        :is-liked="isLiked"
        :is-later="isLater"
        :is-read="isRead"
        @close="showMenu = false"
        @toggle-read-status="toggleReadStatus"
        @toggle-like="toggleLikeVideo"
        @toggle-later="toggleLater"
      />
    </Teleport>
  </article>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import ContextMenu from './ContextMenu.vue'
import VideoItemFeedLayout from './VideoItemFeedLayout.vue'
import VideoItemGridLayout from './VideoItemGridLayout.vue'
import VideoItemWorkbenchLayout from './VideoItemWorkbenchLayout.vue'
import useVideoInteraction from '@/features/video/composables/useVideoInteraction'
import { updateVideoReadState } from '@/shared/api'
import { useSystemConfig } from '@/shared/composables/useSystemConfig'
import { useToast } from '@/shared/components/toast/useToast'
import { errorMessage } from '@/shared/lib/errorMessage'
import { formatDate } from '@/shared/lib/dateFormat'
import type { VideoListItem, VideoProfile } from '@/features/video/types/video'
import {
  pickPrimaryProfile,
  profileDisplayNames,
} from '@/features/video/composables/useProfileNavigation'
import { prefetchDesktopPlaybackSource } from '@/features/video/composables/useVideoOperations'

const props = withDefaults(defineProps<{
  video: VideoListItem
  showAvatar?: boolean
  sortBy?: string
  layout?: 'grid' | 'list'
  showDuration?: boolean
  thumbnailProgress?: boolean
  appearance?: 'default' | 'workbench'
}>(), {
  showAvatar: false,
  layout: 'grid',
  showDuration: true,
  thumbnailProgress: true,
  appearance: 'default',
})

const emit = defineEmits<{
  goToProfile: [profile: VideoProfile]
  /** @deprecated prefer goToProfile */
  goToSubscription: [id: number | string]
  openModal: [video: VideoListItem]
}>()

const { config: systemConfig } = useSystemConfig()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()
const toast = useToast()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })

const isRead = ref(false)
const isLiked = ref<number | null>(null)
const isLater = ref<number | null>(null)

function hydrateFromVideo(video: VideoListItem) {
  isRead.value = video.is_read ?? Number(video.last_position || 0) > 0
  const type = video.interaction_type
  isLiked.value = type === INTERACTION_TYPE.LIKE ? 1 : null
  isLater.value = type === INTERACTION_TYPE.LATER ? 1 : null
}

hydrateFromVideo(props.video)

watch(
  () => [props.video.id, props.video.is_read, props.video.interaction_type, props.video.last_position] as const,
  () => hydrateFromVideo(props.video),
)

const thumbnailSrc = computed(() => String(props.video?.thumbnail || '').trim())
const isNsfwVideo = computed(() => props.video.subscriptions?.some((s) => s.is_nsfw))
const shouldBlurThumbnail = computed(() => Boolean(systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value))

const progressRatio = computed(() => {
  const d = Number(props.video?.duration || 0)
  return d > 0 ? Math.min(1, Number(props.video?.last_position || 0) / d) : 0
})

const displayDateText = computed(() => {
  const t = props.sortBy === 'created_at'
    ? (props.video.created_at || props.video.uploaded_at)
    : (props.video.uploaded_at || props.video.created_at)
  return t ? formatDate(t) : ''
})

const displayNames = computed(() => profileDisplayNames(props.video, '未知'))

const primaryProfile = computed(() => pickPrimaryProfile(props.video))

const thumbnailPresentation = computed(() => ({
  src: thumbnailSrc.value,
  title: props.video.title,
  duration: props.showDuration ? props.video.duration : null,
  progressRatio: progressRatio.value,
  showProgress: props.thumbnailProgress,
  blur: shouldBlurThumbnail.value,
}))

const profilePresentation = computed(() => ({
  profile: primaryProfile.value,
  names: displayNames.value,
  dateText: displayDateText.value,
  site: props.video.site,
  showAvatar: props.showAvatar,
}))

const actionPresentation = computed(() => ({
  isLiked: isLiked.value === 1,
  isRead: isRead.value,
  isLater: isLater.value === 1,
}))

const closeMenuOnExternalClose = () => { showMenu.value = false }

const showContextMenu = async (event: MouseEvent) => {
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))
  await nextTick()
  menuPosition.value = { x: event.clientX, y: event.clientY }
  showMenu.value = true
}

const handleOpen = () => emit('openModal', props.video)

const prefetchPlayback = () => {
  void prefetchDesktopPlaybackSource(props.video)
}

const goToProfile = (profile: VideoProfile | null | undefined) => {
  if (!profile) return
  let source = profile.profile_source
  if (!source) {
    const id = profile.id
    const inSubs = (props.video.subscriptions || []).some((s) => s.id === id && id != null)
    const inActors = (props.video.actors || []).some((a) => a.id === id && id != null)
    if (inSubs) source = 'subscription'
    else if (inActors) source = 'creator'
  }
  const resolved: VideoProfile = source ? { ...profile, profile_source: source } : profile
  emit('goToProfile', resolved)
  if (resolved.profile_source === 'subscription' && resolved.id != null && resolved.id !== '') {
    emit('goToSubscription', resolved.id)
  }
}

const toggleReadStatus = async (markRead: boolean) => {
  const previous = isRead.value
  isRead.value = markRead
  try {
    await updateVideoReadState(props.video.id, markRead)
  } catch (err) {
    isRead.value = previous
    toast.error(errorMessage(err, markRead ? '标记已读失败' : '标记未读失败'))
  }
  showMenu.value = false
}

const setExclusiveInteraction = async (next: 'like' | 'later' | null) => {
  const prevLiked = isLiked.value
  const prevLater = isLater.value

  if (next === 'like') {
    isLiked.value = 1
    isLater.value = null
  } else if (next === 'later') {
    isLater.value = 1
    isLiked.value = null
  } else {
    isLiked.value = null
    isLater.value = null
  }

  try {
    if (next === 'like') {
      await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
    } else if (next === 'later') {
      await toggleLike(props.video.id, INTERACTION_TYPE.LATER)
    } else {
      await deleteInteraction(props.video.id)
    }
  } catch (err) {
    isLiked.value = prevLiked
    isLater.value = prevLater
    toast.error(errorMessage(err, '更新互动状态失败'))
  }
}

const toggleLikeVideo = async () => {
  await setExclusiveInteraction(isLiked.value === 1 ? null : 'like')
  showMenu.value = false
}

const toggleLater = async () => {
  await setExclusiveInteraction(isLater.value === 1 ? null : 'later')
  showMenu.value = false
}

onMounted(() => document.addEventListener('closeAllContextMenus', closeMenuOnExternalClose))
onUnmounted(() => document.removeEventListener('closeAllContextMenus', closeMenuOnExternalClose))
</script>

<style src="../../styles/video-item.css"></style>
