<template>
  <div
    class="video-item bg-card rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-300 relative"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <div class="video-thumbnail relative cursor-pointer overflow-hidden group transform-gpu">
      <img
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        class="w-full h-full object-cover absolute top-0 left-0 transform-gpu will-change-transform transition-transform duration-300 group-hover:scale-105"
        :class="{ 'blur-thumbnail': shouldBlurThumbnail }"
        @error="handleThumbnailError"
        :alt="video.title"
      >

      <!-- 添加默认封面 -->
      <div
        v-if="showDefaultThumbnail"
        class="w-full h-full absolute top-0 left-0 bg-muted flex items-center justify-center"
      >
        <div class="text-muted-foreground flex flex-col items-center">
          <Icon icon="material-symbols:image" class="text-4xl mb-2" />
          <span class="text-xs">暂无封面</span>
        </div>
      </div>

      <div class="video-duration absolute bottom-1 right-1 bg-muted/70 text-foreground text-2xs px-1 py-0.5 rounded">
        {{ formatDuration(video.duration) }}
      </div>
      <div class="absolute inset-0 bg-muted opacity-0 group-hover:opacity-20 transition-opacity duration-300"></div>

      <div
        v-if="showProgress && progress > 0"
        class="absolute bottom-0 left-0 right-0 h-[2px] bg-muted/40 backdrop-blur-sm"
      >
        <div
          class="h-full bg-primary/90 transition-all duration-200"
          :style="{
            width: `${(progress * 100).toFixed(1)}%`,
            borderRadius: '1px'
          }"
        ></div>
      </div>
    </div>
    <div class="video-item-content">
      <h5
        class="text-2xs text-foreground font-medium line-clamp-2 h-8 cursor-pointer hover:text-blue-500 transition-colors duration-200"
      >
        {{ video.title }}
      </h5>
      <div class="video-item-meta text-2xs text-muted-foreground">
        <div class="relative group flex-1 min-w-0">
          <div class="flex items-center min-w-0">
            <div class="flex -space-x-2 relative">
              <div
                v-for="(avatar, index) in displayAvatars"
                :key="`avatar-${index}`"
                class="contents"
              >
                <img
                  v-if="index < 3"
                  :src="getAvatarSrc(avatar.avatar, 'video-avatar-' + video.id + '-' + index)"
                  class="w-4 h-4 rounded-full object-cover flex-shrink-0 cursor-pointer ring-1 ring-card"
                  :class="{'relative z-30': index === 0, 'relative z-20': index === 1, 'relative z-10': index === 2}"
                  referrerpolicy="no-referrer"
                  @error="(e) => handleAvatarError(e, 'video-avatar-' + video.id + '-' + index)"
                  @click.stop="goToSubscription(avatar.id)"
                  :alt="avatar.name"
                >
              </div>
            </div>
            <span
              class="text-2xs text-muted-foreground ml-2 truncate cursor-pointer hover:text-blue-500 transition-colors flex-1 min-w-0 block"
              @click.stop="goToSubscription(video.subscriptions[0]?.id)"
              :title="displayNames"
            >
              {{ displayNames }}
            </span>
            <button
              v-if="hasActors"
              class="actor-toggle ml-1 text-2xs text-muted-foreground hover:text-foreground opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity"
              type="button"
              @click.stop="toggleActors"
              aria-label="显示订阅列表"
              :aria-expanded="showActors"
            >
              ...
            </button>
          </div>

          <!-- 悬浮模态框 -->
          <div
            v-if="hasActors"
            class="channel-popup opacity-0 invisible group-hover:opacity-100 group-hover:visible absolute left-0 bottom-full mb-2 bg-card rounded-lg shadow-lg transition-all duration-200 z-50 w-max max-w-72 p-3"
            :class="{ 'is-visible': showActors }"
          >
            <!-- 订阅列表 -->
            <div class="flex flex-col gap-2">
              <div
                v-for="subscription in video.subscriptions"
                :key="subscription.subscription_id"
                class="flex items-center group/actor cursor-pointer hover:bg-accent p-1 rounded-lg transition-colors duration-150"
                @click.stop="goToSubscription(subscription.id)"
              >
                <img
                  :src="getAvatarSrc(subscription.avatar, 'video-popup-avatar-' + subscription.subscription_id)"
                  alt="Actor Avatar"
                  class="w-6 h-6 rounded-full mr-2 object-cover"
                  referrerpolicy="no-referrer"
                  @error="(e) => handleAvatarError(e, 'video-popup-avatar-' + subscription.subscription_id)"
                >
                <span class="text-muted-foreground group-hover/actor:text-foreground transition-colors duration-150">
                  {{ subscription.name }}
                </span>
              </div>
            </div>

            <!-- 小三角形 -->
            <div class="absolute -bottom-2 left-4 w-4 h-4 bg-card transform rotate-45"></div>
          </div>
        </div>
        <span class="leading-4 font-medium flex-shrink-0 ml-2">{{ displayDateText }}</span>
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
import { onMounted, onUnmounted, ref, nextTick, computed, watch, toRef } from 'vue';
import ContextMenu from './ContextMenu.vue';
import useOptionsMenu from '@/composables/useOptionsMenu';
import useVideoHistory from '@/composables/useVideoHistory';
import useVideoInteraction from '@/composables/useVideoInteraction';
import { formatDate, formatDuration } from '@/utils/dateFormat';
import { Icon } from '@iconify/vue';
import { useImageFallback } from '@/composables/useImageFallback';
import { useSystemConfig } from '@/composables/useSystemConfig';
import { Logger } from '@/utils/logger';

const props = defineProps({
  video: {
    type: Object,
    required: true,
  },
  showAvatar: {
    type: Boolean,
    default: true
  },
  showProgress: {
    type: Boolean,
    default: false
  },
  progress: {
    type: Number,
    default: 0
  },
  sortBy: {
    type: String,
    default: 'publish_date'
  }
});

const emit = defineEmits([
  'goToSubscription',
  'openModal',
]);

const { config: systemConfig } = useSystemConfig();
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();
const { copyVideoLink } = useOptionsMenu(toRef(props, 'video'));
const { clearHistory, sendReport } = useVideoHistory();
const { INTERACTION_TYPE, toggleLike, deleteInteraction } = useVideoInteraction();

const isNsfwVideo = computed(() => {
  return props.video.subscriptions?.some(sub => sub.is_nsfw) || false;
});

const shouldBlurThumbnail = computed(() => {
  return systemConfig.value?.blur_nsfw_thumbnails && isNsfwVideo.value;
});

const displayDateText = computed(() => {
  const sortBy = props.sortBy;
  const ts = sortBy === 'created_at'
    ? (props.video.created_at || props.video.uploaded_at)
    : (props.video.uploaded_at || props.video.created_at);

  return ts ? formatDate(ts) : '';
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll, true);
});

const showMenu = ref(false);
const menuPosition = ref({ x: 0, y: 0 });
const showActors = ref(false);

const showContextMenu = async (event) => {
  event.preventDefault();
  event.stopPropagation();
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'));

  await nextTick();

  const x = event.clientX;
  const y = event.clientY;

  menuPosition.value = { x, y };
  showMenu.value = true;
};

const closeContextMenu = () => {
  showMenu.value = false;
};

const handleScroll = () => {
  if (showMenu.value) {
    closeContextMenu();
  }
};

const handleClick = () => {
  emit('openModal', props.video);
};

const hasActors = computed(() => props.video.subscriptions.length > 1);

const goToSubscription = (subscriptionId) => {
  emit('goToSubscription', subscriptionId);
};

const toggleActors = () => {
  showActors.value = !showActors.value;
};

const toggleReadStatus = async (isRead) => {
  try {
    if (isRead) {
      const position = Number(props.video.duration || props.video.last_position || 0);
      await sendReport(props.video.id, position, { force: true });
      props.video.is_read = true;
      props.video.last_position = position;
    } else {
      await clearHistory([props.video.id]);
      props.video.is_read = false;
      props.video.last_position = 0;
    }
    closeContextMenu();
  } catch (error) {
    Logger.error('Failed to update read status', error);
  }
};

const toggleLikeVideo = async () => {
  try {
    if (props.video.is_liked === 1 || props.video.is_liked === 0) {
      const { error } = await deleteInteraction(props.video.id);
      if (!error) {
        props.video.is_liked = null;
      }
    } else {
      const { error } = await toggleLike(props.video.id, INTERACTION_TYPE.LIKE);
      if (!error) {
        props.video.is_liked = 1;
      }
    }
    closeContextMenu();
  } catch (error) {
    Logger.error('Failed to toggle like state', error);
  }
};

watch(showMenu, (isOpen) => {
  if (isOpen) {
    nextTick(() => {
      document.addEventListener('click', closeContextMenu, { once: true });
      window.addEventListener('scroll', handleScroll, { passive: true, capture: true, once: true });
    });
  }
});

onMounted(() => {
  document.addEventListener('closeAllContextMenus', closeContextMenu);
});

onUnmounted(() => {
  document.removeEventListener('closeAllContextMenus', closeContextMenu);
});

const displayAvatars = computed(() => {
  let avatars = props.video.subscriptions?.map(sub => ({
    id: sub.id,
    name: sub.name,
    avatar: sub.avatar
  })) || [];

  if (!avatars.length && props.video.actors) {
    avatars = props.video.actors.map(actor => ({
      id: actor.id,
      name: actor.name,
      avatar: actor.avatar
    }));
  }

  return avatars.slice(0, 3);
});

const displayNames = computed(() => {
  return displayAvatars.value
    .slice(0, 2)
    .map(avatar => avatar.name)
    .join(', ');
});

const showDefaultThumbnail = ref(false);

const handleThumbnailError = () => {
  showDefaultThumbnail.value = true;
};

</script>

<style scoped>
.video-item {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  break-inside: avoid;
}

.video-thumbnail {
  flex: none;
  position: relative;
  padding-top: 56.25%; /* 16:9 宽高比 */
  background-color: hsl(var(--muted));
}

.video-item-content {
  flex: none;
  height: 68px;
  padding: 8px;
  box-sizing: border-box;
}

.video-item-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-height: 16px;
  margin-top: 4px;
}

.video-thumbnail img,
.video-thumbnail .video-player {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.video-duration {
  position: absolute;
  bottom: 4px;
  right: 4px;
  background-color: var(--overlay-dark-70);
  color: hsl(var(--foreground));
  font-size: var(--font-size-2xs);
  padding: 2px 4px;
  border-radius: 2px;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.context-menu-item {
  @apply px-4 py-2 text-sm text-foreground hover:bg-accent cursor-pointer flex items-center;
}

.cursor-pointer {
  cursor: pointer;
}

@media (max-width: 768px) {
  .text-2xs {
    font-size: var(--font-size-3xs);
  }
}

.video-item.border-2 {
  box-shadow: 0 0 0 2px hsl(var(--ring));
}

.gap-1 {
  gap: 0.25rem;
}

.leading-3 {
  line-height: 0.75rem;
}

.channel-popup {
  transform-origin: top left;
  box-shadow: var(--shadow-popup);
}

.channel-popup.is-visible {
  opacity: 1;
  visibility: visible;
  z-index: 1000;
}

.group:focus-within .channel-popup {
  opacity: 1;
  visibility: visible;
  z-index: 1000;
}

@media (hover: none) {
  .actor-toggle {
    opacity: 1;
  }
}

.channel-popup::before {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  top: -8px;
  height: 8px;
  background: transparent;
}

.group:hover .channel-popup {
  z-index: 1000;
}

.group-hover\:opacity-100 {
  transition-delay: 200ms;
}

.group:not(:hover) .channel-popup {
  transition-delay: 0ms;
}

.video-thumbnail:hover .bg-primary\/90 {
  height: 3px;
  margin-top: -1px;
}

.video-thumbnail:hover .h-\[2px\] {
  height: 2px;
}

.video-item {
  position: relative;
  z-index: 1;
  cursor: pointer;
}

.video-thumbnail {
  position: relative;
  z-index: 1;
}

.ring-1 {
  --tw-ring-offset-shadow: 0 0 #0000;
  --tw-ring-shadow: 0 0 0 1px var(--tw-ring-color);
  box-shadow: var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow, 0 0 #0000);
}

.-space-x-2 > :not([hidden]) ~ :not([hidden]) {
  --tw-space-x-reverse: 0;
  margin-right: calc(-0.5rem * var(--tw-space-x-reverse));
  margin-left: calc(-0.5rem * calc(1 - var(--tw-space-x-reverse)));
}

@media (max-width: 500px) {
  .video-item {
    width: 100%;
  }

  .video-thumbnail {
    padding-top: 56.25%; /* 保持16:9比例 */
  }
}

.default-avatar {
  @apply bg-muted text-foreground flex items-center justify-center text-2xs font-medium;
}

.blur-thumbnail {
  filter: blur(20px);
  transition: filter 0.3s ease-in-out;
}

.video-thumbnail:hover .blur-thumbnail {
  filter: blur(0px);
}
</style>
