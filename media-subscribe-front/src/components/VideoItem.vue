<template>
  <div 
    class="video-item bg-white rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200"
    @contextmenu.prevent="showContextMenu"
  >
    <div class="video-thumbnail relative cursor-pointer" @click="$emit('openModal', video)" ref="imageRef">
      <img
        v-if="isImageLoaded"
        :src="video.thumbnail"
        referrerpolicy="no-referrer"
        alt="Video thumbnail"
        class="w-full h-full object-cover absolute top-0 left-0"
      >
      <div class="video-duration absolute bottom-1 right-1 bg-black bg-opacity-70 text-white text-2xs px-1 py-0.5 rounded">
        {{ formatDuration(video.duration) }}
      </div>
    </div>
    <div class="p-2">
      <h3 
        class="text-xs font-medium text-gray-900 line-clamp-2 h-9 cursor-pointer hover:text-blue-600"
        @click="openVideoLink"
      >
        {{ video.title }}
      </h3>
      <div class="flex items-center justify-between text-2xs text-gray-500 mt-1">
        <span class="truncate">{{ video.channel_name }}</span>
        <span>{{ formatDate(video.uploaded_at) }}</span>
      </div>
    </div>
    <Teleport to="body">
      <ContextMenu 
        v-if="showMenu"
        :position="menuPosition"
        :isOpen="showMenu"
        :isChannelPage="isChannelPage"
        :activeTab="activeTab"
        @close="closeContextMenu"
        @toggleReadStatus="toggleReadStatus"
        @markReadBatch="markReadBatch"
        @downloadVideo="downloadVideo"
        @copyVideoLink="copyVideoLink"
        @dislikeVideo="dislikeVideo"
      />
    </Teleport>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted, ref, nextTick } from 'vue';
import ContextMenu from './ContextMenu.vue';
import useOptionsMenu from "../composables/useOptionsMenu.js";

const props = defineProps({
  video: Object,
  showAvatar: {
    type: Boolean,
    default: true
  },
  isChannelPage: Boolean,
  activeTab: String,
  setVideoRef: Function,
  refreshContent: Function, // 添加这一行
});

const emit = defineEmits([
  'setVideoRef',
  'goToChannel',
  'openModal', 'downloadVideo'
]);

const imageRef = ref(null);
const isImageLoaded = ref(false);

onMounted(() => {
  const options = {
    root: null,
    rootMargin: '100px', // 预加载范围扩大
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

const showMenu = ref(false);
const menuPosition = ref({ x: 0, y: 0 });

const {
  toggleReadStatus,
  markReadBatch,
  downloadVideo,
  copyVideoLink,
  dislikeVideo,
} = useOptionsMenu(props.video, props.refreshContent);

const showContextMenu = async (event) => {
  event.preventDefault();
  // 关闭所有其他的上下文菜单
  document.dispatchEvent(new CustomEvent('closeAllContextMenus'));
  
  await nextTick();
  
  // 使用全局坐标
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

const openVideoLink = () => {
  if (props.video && props.video.url) {
    window.open(props.video.url, '_blank');
  }
};

document.addEventListener('closeAllContextMenus', closeContextMenu);
document.addEventListener('click', closeContextMenu);

onUnmounted(() => {
  document.removeEventListener('closeAllContextMenus', closeContextMenu);
  document.removeEventListener('click', closeContextMenu);
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
  background-color: #f0f0f0; /* 添加背景色 */
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

.cursor-pointer {
  cursor: pointer;
}

.hover\:text-blue-600:hover {
  color: #2563eb;
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
</style>
