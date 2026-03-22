<template>
  <div
    class="video-item video-card"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <div class="video-thumbnail video-card-thumbnail group">
      <img
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        class="video-card__image"
        :class="{ 'blur-thumbnail': shouldBlurThumbnail }"
        :alt="video.title"
        @error="handleThumbnailError"
      >

      <div
        v-if="showDefaultThumbnail"
        class="video-card__fallback"
      >
        <div class="video-card__fallback-inner">
          <Icon icon="material-symbols:image" class="video-card__fallback-icon" />
          <span class="video-card__fallback-text">暂无封面</span>
        </div>
      </div>

      <div class="video-card__overlay"></div>

      <div class="video-card__topline">
        <Badge v-if="isUnread" variant="secondary" class="video-card__badge video-card__badge--unread">
          未读
        </Badge>
        <Badge v-if="isNsfwVideo" variant="destructive" class="video-card__badge">
          NSFW
        </Badge>
        <Badge v-if="isLikedVideo" variant="outline" class="video-card__badge video-card__badge--liked">
          喜欢
        </Badge>
      </div>

      <div class="video-card__bottomline">
        <div
          v-if="showProgress && progress > 0"
          class="video-progress-bar"
        >
          <div
            class="video-progress-indicator"
            :style="{ width: `${(progress * 100).toFixed(1)}%` }"
          ></div>
        </div>
        <div class="video-duration">
          {{ formatDuration(video.duration) }}
        </div>
      </div>
    </div>

    <div class="video-item-content video-info">
      <h5 class="video-title">
        {{ video.title }}
      </h5>

      <div class="video-card__meta-row">
        <div class="video-card__channel-wrap">
          <div v-if="showAvatar && displayAvatars.length" class="author-avatars">
            <img
              v-for="(avatar, index) in displayAvatars"
              :key="`avatar-${index}`"
              :src="getAvatarSrc(avatar.avatar, `video-avatar-${video.id}-${index}`)"
              class="author-avatar"
              :class="{
                'author-avatar--front': index === 0,
                'author-avatar--middle': index === 1,
                'author-avatar--back': index === 2,
              }"
              referrerpolicy="no-referrer"
              :alt="avatar.name"
              @error="(event) => handleAvatarError(event, `video-avatar-${video.id}-${index}`)"
              @click.stop="goToSubscription(avatar.id)"
            >
          </div>

          <button
            type="button"
            class="video-card__channel-name"
            :title="displayNames"
            @click.stop="goToSubscription(primarySubscriptionId)"
          >
            {{ displayNames }}
          </button>

          <button
            v-if="hasActors"
            type="button"
            class="actor-toggle"
            :aria-expanded="showActors"
            aria-label="显示订阅列表"
            @click.stop="toggleActors"
          >
            +{{ hiddenActorCount }}
          </button>

          <div
            v-if="hasActors"
            class="channel-popup"
            :class="{ 'is-visible': showActors }"
          >
            <div class="channel-popup__list">
              <button
                v-for="subscription in video.subscriptions"
                :key="subscription.subscription_id"
                type="button"
                class="channel-popup__item"
                @click.stop="goToSubscription(subscription.id)"
              >
                <img
                  :src="getAvatarSrc(subscription.avatar, `video-popup-avatar-${subscription.subscription_id}`)"
                  alt="subscription avatar"
                  class="channel-popup__avatar"
                  referrerpolicy="no-referrer"
                  @error="(event) => handleAvatarError(event, `video-popup-avatar-${subscription.subscription_id}`)"
                >
                <span class="channel-popup__name">{{ subscription.name }}</span>
              </button>
            </div>
            <div class="channel-popup__arrow"></div>
          </div>
        </div>

        <span class="video-card__date">{{ displayDateText }}</span>
      </div>

      <div class="video-card__footer">
        <span v-if="resumeText" class="video-card__resume">{{ resumeText }}</span>
        <span v-if="isDislikedVideo" class="video-card__status">已标记不喜欢</span>
      </div>
    </div>

    <Teleport to="body">
      <ContextMenu
        v-if="showMenu"
        :position="menuPosition"
        :is-open="showMenu"
        :video="video"
        @close="closeContextMenu"
        @toggleReadStatus="toggleReadStatus"
        @copyVideoLink="copyVideoLink"
        @toggleLike="toggleLikeVideo"
      />
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, toRef, watch } from 'vue'
import { Icon } from '@iconify/vue'
import { Badge } from '@/components/ui/badge'
import ContextMenu from './ContextMenu.vue'
import useOptionsMenu from '@/composables/useOptionsMenu'
import useVideoHistory from '@/composables/useVideoHistory'
import useVideoInteraction from '@/composables/useVideoInteraction'
import { useImageFallback } from '@/composables/useImageFallback'
import { useSystemConfig } from '@/composables/useSystemConfig'
import { formatDate, formatDuration } from '@/utils/dateFormat'
import { Logger } from '@/utils/logger'

const props = defineProps({
  video: {
    type: Object,
    required: true,
  },
  showAvatar: {
    type: Boolean,
    default: true,
  },
  showProgress: {
    type: Boolean,
    default: false,
  },
  progress: {
    type: Number,
    default: 0,
  },
  sortBy: {
    type: String,
    default: 'publish_date',
  },
})

const emit = defineEmits([
  'goToSubscription',
  'openModal',
])

const { config: systemConfig } = useSystemConfig()
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback()
const { copyVideoLink } = useOptionsMenu(toRef(props, 'video'))
const { clearHistory, sendReport } = useVideoHistory()
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction()

const showMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })
const showActors = ref(false)
const showDefaultThumbnail = ref(false)

const isNsfwVideo = computed(() => props.video.subscriptions?.some((subscription) => subscription.is_nsfw) || false)
const shouldBlurThumbnail = computed(() => systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value)
const isUnread = computed(() => !props.video.is_read)
const isLikedVideo = computed(() => props.video.is_liked === 1)
const isDislikedVideo = computed(() => props.video.is_liked === 0)

const displayDateText = computed(() => {
  const timestamp = props.sortBy === 'created_at'
    ? (props.video.created_at || props.video.uploaded_at)
    : (props.video.uploaded_at || props.video.created_at)

  return timestamp ? formatDate(timestamp) : ''
})

const displayAvatars = computed(() => {
  let avatars = props.video.subscriptions?.map((subscription) => ({
    id: subscription.id,
    name: subscription.name,
    avatar: subscription.avatar,
  })) || []

  if (!avatars.length && props.video.actors) {
    avatars = props.video.actors.map((actor) => ({
      id: actor.id,
      name: actor.name,
      avatar: actor.avatar,
    }))
  }

  return avatars.slice(0, 3)
})

const displayNames = computed(() => {
  const names = displayAvatars.value.map((avatar) => avatar.name)

  if (!names.length) {
    return '未知频道'
  }

  return names.join(' · ')
})

const primarySubscriptionId = computed(() => {
  return props.video.subscriptions?.[0]?.id ?? displayAvatars.value[0]?.id
})

const hasActors = computed(() => (props.video.subscriptions?.length || 0) > 1)
const hiddenActorCount = computed(() => Math.max((props.video.subscriptions?.length || 0) - 1, 0))

const resumeText = computed(() => {
  const duration = Number(props.video.duration || 0)
  const lastPosition = Number(props.video.last_position || 0)

  if (!duration || !lastPosition || props.video.is_read) {
    return ''
  }

  const percent = Math.max(1, Math.min(99, Math.round((lastPosition / duration) * 100)))
  return `已看到 ${percent}%`
})

const closeContextMenu = () => {
  showMenu.value = false
}

const handleScroll = () => {
  if (showMenu.value) {
    closeContextMenu()
  }
}

const showContextMenu = async (event) => {
  event.preventDefault()
  event.stopPropagation()
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'))

  await nextTick()

  menuPosition.value = {
    x: event.clientX,
    y: event.clientY,
  }
  showMenu.value = true
}

const handleClick = () => {
  emit('openModal', props.video)
}

const goToSubscription = (subscriptionId) => {
  if (!subscriptionId) return
  emit('goToSubscription', subscriptionId)
}

const toggleActors = () => {
  showActors.value = !showActors.value
}

const toggleReadStatus = async (isRead) => {
  try {
    if (isRead) {
      const position = Number(props.video.duration || props.video.last_position || 0)
      await sendReport(props.video.id, position, { force: true })
      props.video.is_read = true
      props.video.last_position = position
    } else {
      await clearHistory([props.video.id])
      props.video.is_read = false
      props.video.last_position = 0
    }

    closeContextMenu()
  } catch (error) {
    Logger.error('Failed to update read status', error)
  }
}

const toggleLikeVideo = async () => {
  try {
    if (props.video.is_liked === 1 || props.video.is_liked === 0) {
      const { error } = await deleteInteraction(props.video.id)
      if (!error) {
        props.video.is_liked = null
      }
    } else {
      const { error } = await toggleLike(props.video.id, INTERACTION_TYPE.LIKE)
      if (!error) {
        props.video.is_liked = 1
      }
    }

    closeContextMenu()
  } catch (error) {
    Logger.error('Failed to toggle like state', error)
  }
}

const handleThumbnailError = () => {
  showDefaultThumbnail.value = true
}

watch(showMenu, (isOpen) => {
  if (isOpen) {
    nextTick(() => {
      document.addEventListener('click', closeContextMenu, { once: true })
      window.addEventListener('scroll', handleScroll, { passive: true, capture: true, once: true })
    })
  }
})

onMounted(() => {
  document.addEventListener('closeAllContextMenus', closeContextMenu)
})

onUnmounted(() => {
  document.removeEventListener('closeAllContextMenus', closeContextMenu)
  window.removeEventListener('scroll', handleScroll, true)
})
</script>

<style scoped src="../../styles/components/video-card.css"></style>
