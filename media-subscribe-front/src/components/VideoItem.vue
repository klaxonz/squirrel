<template>
  <div 
    class="video-item bg-[#212121] rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 ease-in-out transform hover:-translate-y-1 relative"
    @contextmenu.prevent="showContextMenu"
    @click="handleClick"
  >
    <div class="video-thumbnail relative cursor-pointer overflow-hidden group" ref="imageRef">
      <img
        v-if="isImageLoaded"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        alt="Video thumbnail"
        class="w-full h-full object-cover absolute top-0 left-0 transition-transform duration-300 group-hover:scale-105"
      >
      <div v-else class="w-full h-full bg-gray-200 animate-pulse"></div>
      
      <div class="video-duration absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-2xs px-1 py-0.5 rounded">
        {{ formatDuration(video.duration) }}
      </div>
      <div class="absolute inset-0 bg-black opacity-0 group-hover:opacity-20 transition-opacity duration-300"></div>

      <div
        v-if="showProgress && progress > 0" 
        class="absolute bottom-0 left-0 right-0 h-[2px] bg-black/40 backdrop-blur-sm"
      >
        <div 
          class="h-full bg-red-600/90 transition-all duration-200"
          :style="{ 
            width: `${(progress * 100).toFixed(1)}%`,
            borderRadius: '1px'
          }"
        ></div>
      </div>
    </div>
    <div class="p-2">
      <h5 
        class="text-[10px] text-white font-medium line-clamp-2 h-8 cursor-pointer hover:text-blue-400 transition-colors duration-200"
      >
        {{ video.title }}
      </h5>
      <div class="flex items-center justify-between text-2xs text-gray-400 pt-1">
        <div class="relative group">
          <div class="flex items-center">
            <div class="flex -space-x-2 relative">
              <template v-for="(avatar, index) in displayAvatars" :key="index">
                <img 
                  v-if="index < 3"
                  :src="avatar.avatar" 
                  :alt="`${avatar.name} Avatar`" 
                  class="w-4 h-4 rounded-full object-cover flex-shrink-0 cursor-pointer ring-1 ring-[#212121]"
                  :class="{'relative z-30': index === 0, 'relative z-20': index === 1, 'relative z-10': index === 2}"
                  referrerpolicy="no-referrer"
                  @click.stop="goToSubscription(avatar.id)"
                >
              </template>
            </div>
            <span class="text-2xs text-gray-400 ml-2 truncate">
              {{ displayNames }}
            </span>
          </div>

          <!-- 悬浮模态框 -->
          <div 
            v-if="hasActors"
            class="channel-popup opacity-0 invisible group-hover:opacity-100 group-hover:visible absolute left-0 bottom-full mb-2 bg-[#282828] rounded-lg shadow-lg transition-all duration-200 z-50 w-max max-w-[300px] p-3"
          >
            <!-- 订阅列表 -->
            <div class="flex flex-col gap-2">
              <div 
                v-for="subscription in video.subscriptions"
                :key="subscription.subscription_id"
                class="flex items-center group/actor cursor-pointer hover:bg-gray-700/50 p-1 rounded-lg transition-colors duration-150"
                @click.stop="goToSubscription(subscription.subscription_id)"
              >
                <img 
                  :src="subscription.avatar_url"
                  alt="Actor Avatar" 
                  class="w-6 h-6 rounded-full mr-2 object-cover"
                  referrerpolicy="no-referrer"
                >
                <span class="text-gray-300 group-hover/actor:text-white transition-colors duration-150">
                  {{ subscription.content_name }}
                </span>
              </div>
            </div>
            
            <!-- 小三角形 -->
            <div class="absolute -bottom-2 left-4 w-4 h-4 bg-[#282828] transform rotate-45"></div>
          </div>
        </div>
        <span class="leading-4 font-medium">{{ formatDate(video.uploaded_at) }}</span>
      </div>
    </div>
    <Teleport to="body">
      <ContextMenu 
        v-if="showMenu"
        :position="menuPosition"
        :is-open="showMenu"
        :is-read="video.is_read"
        :video="video"
        @close="closeContextMenu"
        @toggleReadStatus="toggleReadStatus"
        @markReadBatch="markReadBatch"
        @downloadVideo="downloadVideo"
        @copyVideoLink="copyVideoLink"
        @dislikeVideo="dislikeVideo"
        @toggleLike="toggleLikeVideo"
      />
    </Teleport>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted, ref, nextTick, inject, computed, watch, toRef } from 'vue';
import ContextMenu from './ContextMenu.vue';
import useOptionsMenu from "../composables/useOptionsMenu.js";
import { formatDate, formatDuration } from '../utils/dateFormat';

const props = defineProps({
  video: {
    type: Object,
    required: true,
  },
  showAvatar: {
    type: Boolean,
    default: true
  },
  setVideoRef: Function,
  showProgress: {
    type: Boolean,
    default: false
  },
  progress: {
    type: Number,
    default: 0
  }
});

const emit = defineEmits([
  'goToSubscription',
  'openModal', 
  'downloadVideo',
]);


const imageRef = ref(null);
const isImageLoaded = ref(false);

onMounted(() => {
  const options = {
    root: null,
    rootMargin: '100px',
    threshold: 0.1
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting && !isImageLoaded.value) {
        const img = new Image();
        img.src = props.video.thumbnail;
        img.onload = () => {
          isImageLoaded.value = true;
        };
        observer.unobserve(entry.target);
      }
    });
  }, options);

  if (imageRef.value) {
    observer.observe(imageRef.value);
  }

  return () => {
    if (imageRef.value) {
      observer.unobserve(imageRef.value);
    }
  };
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll, true);
});

const showMenu = ref(false);
const menuPosition = ref({ x: 0, y: 0 });

const videoRef = toRef(props, 'video');
const {
  toggleReadStatus,
  markReadBatch,
  downloadVideo,
  copyVideoLink,
  dislikeVideo,
  toggleLikeVideo,
} = useOptionsMenu(videoRef);

watch(() => props.video, (newVideo) => {
  const {
    toggleReadStatus: newToggleReadStatus,
    markReadBatch: newMarkReadBatch,
    downloadVideo: newDownloadVideo,
    copyVideoLink: newCopyVideoLink,
    toggleLikeVideo: newToggleLikeVideo,
  } = useOptionsMenu(newVideo);

  downloadVideo.value = newDownloadVideo;
  toggleReadStatus.value = newToggleReadStatus;
  markReadBatch.value = newMarkReadBatch;
  copyVideoLink.value = newCopyVideoLink;
  toggleLikeVideo.value = newToggleLikeVideo;
}, { deep: true });

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

const handleClick = (event) => {
  emit('openModal', props.video);
};

const hasActors = computed(() => props.video.subscriptions.length > 1);

const goToSubscription = (subscriptionId) => {
  emit('goToSubscription', subscriptionId);
};

onMounted(() => {
  document.addEventListener('closeAllContextMenus', closeContextMenu);
  document.addEventListener('click', closeContextMenu);
  window.addEventListener('scroll', handleScroll, true);
});

onUnmounted(() => {
  document.removeEventListener('closeAllContextMenus', closeContextMenu);
  document.removeEventListener('click', closeContextMenu);
  window.removeEventListener('scroll', handleScroll, true);
});

const displayAvatars = computed(() => {
  // 优先使用 subscriptions
  let avatars = props.video.subscriptions?.map(sub => ({
    id: sub.subscription_id,
    name: sub.content_name,
    avatar: sub.avatar_url
  })) || [];
  
  // 如果 subscriptions 为空，则使用 actors
  if (!avatars.length && props.video.actors) {
    avatars = props.video.actors.map(actor => ({
      id: actor.creator_id,
      name: actor.creator_name,
      avatar: actor.avatar_url
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
</script>

<style scoped>
.video-item {
  width: 100%;
  height: 100%;
  break-inside: avoid;
}

.video-thumbnail {
  position: relative;
  padding-top: 56.25%; /* 16:9 宽高比 */
  background-color: #181818; /* 更深的背景色 */
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
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: 0.75rem;
  padding: 2px 4px;
  border-radius: 2px;
}

.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.text-2xs {
  font-size: 0.625rem; /* 10px */
  line-height: 1rem; /* 16px, 调整行高以匹配头像高度 */
}

.h-9 {
  height: 2.25rem; /* 36px */
}

.context-menu-item {
  @apply px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer flex items-center;
}

.cursor-pointer {
  cursor: pointer;
}

.hover\:text-blue-400:hover {
  color: #60a5fa;
}

/* 添加一些响应式调整 */
@media (max-width: 768px) {
  .text-2xs {
    font-size: 0.5625rem;
  }
  
  .h-9 {
    height: 2rem;
  }
}

.video-item.border-2 {
  box-shadow: 0 0 0 2px theme('colors.blue.500');
}

.gap-1 {
  gap: 0.25rem;
}

.leading-3 {
  line-height: 0.75rem;
}

.channel-popup {
  transform-origin: top left;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.5);
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

/* 确保弹窗在其他元素之上 */
.group:hover .channel-popup {
  z-index: 1000;
}

/* 添加一些动画效果 */
.group-hover\:opacity-100 {
  transition-delay: 200ms;
}

.group:not(:hover) .channel-popup {
  transition-delay: 0ms;
}

/* 添加进度条相关样式 */
.video-thumbnail:hover .bg-red-600\/90 {
  @apply bg-red-500;
  height: 3px;
  margin-top: -1px;
}

/* 确保进度条容器在hover时保持原高度 */
.video-thumbnail:hover .h-\[2px\] {
  height: 2px;
}

/* 修改标题高度 */
.h-8 {
  height: 2rem; /* 32px, 刚好容纳两行文字 */
}

/* 确保点击区域可以正常工作 */
.video-item {
  position: relative;
  z-index: 1;
  cursor: pointer;
}

/* 移除可能影响点击的变换效果 */
.video-item:hover {
  transform: none;
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

.ring-[#212121] {
  --tw-ring-color: #212121;
}

.-space-x-2 > :not([hidden]) ~ :not([hidden]) {
  --tw-space-x-reverse: 0;
  margin-right: calc(-0.5rem * var(--tw-space-x-reverse));
  margin-left: calc(-0.5rem * calc(1 - var(--tw-space-x-reverse)));
}
</style>
