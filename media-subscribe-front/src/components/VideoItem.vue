<template>
  <div 
    class="video-item bg-[#212121] rounded-lg overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 ease-in-out transform hover:-translate-y-1 relative"
    @contextmenu.prevent="showContextMenu"
    :class="{ 'border-2 border-blue-500': isSelected }"
    @click="handleClick"
  >
    <!-- 移除默认显示的勾选框 -->
    
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
      
      <!-- 添加选中状态指示器 -->
      <div v-if="isSelected" class="absolute top-2 left-2 bg-blue-500 text-white rounded-full p-1">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
      </div>
    </div>
    <div class="p-2">
      <h3 
        class="text-xs font-medium text-white line-clamp-2 h-9 cursor-pointer hover:text-blue-400 transition-colors duration-200"
      >
        {{ video.title }}
      </h3>
      <div class="flex items-center justify-between text-2xs text-gray-400 mt-1">
        <div class="flex items-center">
          <img 
            :src="video.channel_avatar" 
            alt="Channel Avatar" 
            class="w-4 h-4 rounded-full mr-1 object-cover flex-shrink-0"
            referrerpolicy="no-referrer"
          >
          <span class="truncate hover:text-blue-400 transition-colors duration-200 leading-4">{{ video.channel_name }}</span>
        </div>
        <span class="leading-4">{{ formatDate(video.uploaded_at) }}</span>
      </div>
    </div>
    <Teleport to="body">
      <ContextMenu 
        v-if="showMenu"
        :position="menuPosition"
        :isOpen="showMenu"
        :isRead="!!video.is_read"
        :isSelected="isSelected"
        @close="closeContextMenu"
        @toggleReadStatus="toggleReadStatus"
        @markReadBatch="markReadBatch"
        @downloadVideo="downloadVideo"
        @copyVideoLink="copyVideoLink"
        @dislikeVideo="dislikeVideo"
        @toggleSelection="$emit('toggleSelection', video.id)"
      />
    </Teleport>
  </div>
</template>

<script setup>
import { defineProps, defineEmits, onMounted, onUnmounted, ref, nextTick, inject } from 'vue';
import ContextMenu from './ContextMenu.vue';
import useOptionsMenu from "../composables/useOptionsMenu.js";

const props = defineProps({
  video: {
    type: Object,
    required: true,
    validator: (value) => {
      if (typeof value.is_read === 'undefined') {
        console.warn('Video object is missing is_read property');
        return false;
      }
      return true;
    }
  },
  showAvatar: {
    type: Boolean,
    default: true
  },
  isChannelPage: Boolean,
  activeTab: String,
  setVideoRef: Function,
  refreshContent: Function,
  isSelected: Boolean,
});

const emit = defineEmits([
  'goToChannel',
  'openModal', 
  'downloadVideo',
  'select',
  'markReadBatch',
  'toggleSelection'
]);

const isSelectionMode = inject('isSelectionMode', ref(false));

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
  event.stopPropagation();
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

const handleClick = (event) => {
  if (isSelectionMode.value) {
    emit('toggleSelection', props.video.id);
  } else {
    emit('openModal', props.video);
  }
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
</style>
