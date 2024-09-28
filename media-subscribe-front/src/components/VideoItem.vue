<template>
  <div 
    class="video-item bg-white rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200"
    @contextmenu.prevent="showContextMenu"
    @touchstart="startLongPress"
    @touchend="cancelLongPress"
    @touchmove="cancelLongPress"
  >
    <div class="video-thumbnail relative cursor-pointer" @click="$emit('openModal', video)">
      <img
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        alt="Video thumbnail"
        class="w-full h-auto object-cover"
        @load="onImageLoad"
      >
      <div class="video-duration absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-2xs px-1 py-0.5 rounded">
        {{ formatDuration(video.duration) }}
      </div>
    </div>
    <div class="p-2">
      <h3 class="text-xs font-medium text-gray-900 line-clamp-2 h-9">{{ video.title }}</h3>
      <div class="flex items-center justify-between text-2xs text-gray-500 mt-1">
        <span class="truncate">{{ video.channel_name }}</span>
        <span>{{ formatDate(video.uploaded_at) }}</span>
      </div>
    </div>
    <ContextMenu 
      v-if="showMenu"
      :position="menuPosition"
      @close="closeContextMenu"
    >
      <div @click="toggleReadStatus" class="context-menu-item">
        <i class="fas fa-check-circle mr-2"></i>标记为{{ video.is_read ? '未读' : '已读' }}
      </div>
      <div @click="downloadVideo" class="context-menu-item">
        <i class="fas fa-download mr-2"></i>下载
      </div>
      <div @click="copyVideoLink" class="context-menu-item">
        <i class="fas fa-link mr-2"></i>复制链接
      </div>
    </ContextMenu>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted, ref } from 'vue';
import ContextMenu from './ContextMenu.vue';

const props = defineProps({
  video: Object,
  showAvatar: {
    type: Boolean,
    default: true
  },
  setVideoRef: Function,
});

const emit = defineEmits([
  'play', 'setVideoRef', 'videoPlay', 'videoPause', 'videoEnded',
  'toggleOptions', 'goToChannel', 'hoverStop', 'hoverPlay',
  'videoEnterViewport', 'videoLeaveViewport',
  'imageLoaded', 'openModal'
]);

const playVideo = () => {
  console.log('Attempting to play video:', props.video);
  emit('play', props.video);
};

const onVideoPlay = () => {
  console.log('Video started playing');
  emit('videoPlay', props.video);
};

const onVideoPause = () => {
  console.log('Video paused');
  emit('videoPause', props.video);
};

const onVideoEnded = () => {
  console.log('Video ended');
  emit('videoEnded', props.video);
};

const videoItemRef = ref(null);
const observer = ref(null);

onMounted(() => {
  observer.value = new IntersectionObserver(
    ([entry]) => {
      if (!entry.isIntersecting && props.video.isPlaying) {
        emit('videoLeaveViewport', props.video);
      }
    },
    { threshold: 0.5 }
  );

  if (videoItemRef.value) {
    observer.value.observe(videoItemRef.value);
  }
});

onUnmounted(() => {
  if (observer.value) {
    observer.value.disconnect();
  }
});

const formatDuration = (seconds) => {
  if (!seconds) return '未知';
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
};

const formatDate = (dateString) => {
  if (!dateString) return '未知日期';
  const date = new Date(dateString);
  const now = new Date();

  // 获取当前日期和目标日期的年、月、日
  const todayYear = now.getFullYear();
  const todayMonth = now.getMonth();
  const todayDay = now.getDate();

  const dateYear = date.getFullYear();
  const dateMonth = date.getMonth();
  const dateDay = date.getDate();

  // 比较日期
  if (dateYear === todayYear && dateMonth === todayMonth && dateDay === todayDay) {
    return '今天';
  }
  if (dateYear === todayYear && dateMonth === todayMonth && dateDay === todayDay - 1) {
    return '昨天';
  }

  const diffTime = Math.abs(now - date);
  const diffDays = diffTime / (1000 * 60 * 60 * 24);

  if (diffDays <= 7) return `${Math.floor(diffDays)}天前`;
  if (diffDays <= 30) return `${Math.floor(diffDays / 7)}周前`;
  if (diffDays <= 365) return `${Math.floor(diffDays / 30)}个月前`;
  return `${Math.floor(diffDays / 365)}年前`;
};

const onImageLoad = () => {
  emit('imageLoaded');
};

const showMenu = ref(false);
const menuPosition = ref({ x: 0, y: 0 });
let longPressTimer = null;

const showContextMenu = (event) => {
  event.preventDefault();
  menuPosition.value = { x: event.clientX, y: event.clientY };
  showMenu.value = true;
};

const closeContextMenu = () => {
  showMenu.value = false;
};

const startLongPress = (event) => {
  longPressTimer = setTimeout(() => {
    menuPosition.value = { x: event.touches[0].clientX, y: event.touches[0].clientY };
    showMenu.value = true;
  }, 500); // 500ms long press
};

const cancelLongPress = () => {
  clearTimeout(longPressTimer);
};

// Add this new function
const handleScroll = () => {
  if (showMenu.value) {
    closeContextMenu();
  }
};

onMounted(() => {
  window.addEventListener('scroll', handleScroll, true);
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll, true);
});
</script>

<style scoped>
.video-item {
  width: 100%;
  break-inside: avoid;
}

.video-thumbnail {
  position: relative;
  padding-top: 56.25%; /* 16:9 宽高比 */
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
  line-height: 0.75rem; /* 12px */
}

.h-9 {
  height: 2.25rem; /* 36px */
}

.context-menu-item {
  @apply px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 cursor-pointer flex items-center;
}
</style>