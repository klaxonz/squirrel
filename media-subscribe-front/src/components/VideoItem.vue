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

      <!-- 添加进度条 - 移动到封面底部 -->
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
      <h3 
        class="text-xs font-medium text-white line-clamp-2 h-8 cursor-pointer hover:text-blue-400 transition-colors duration-200"
      >
        {{ video.title }}
      </h3>
      <div class="flex items-center justify-between text-2xs text-gray-400">
        <div class="relative group">
          <div class="flex items-center">
            <img 
              :src="mainChannelInfo.avatar" 
              alt="Channel Avatar" 
              class="w-4 h-4 rounded-full mr-1 object-cover flex-shrink-0 cursor-pointer"
              referrerpolicy="no-referrer"
              @click.stop="goToChannel(mainChannelInfo.id)"
            >
            <span 
              class="truncate hover:text-blue-400 transition-colors duration-200 leading-4 cursor-pointer" 
              @click.stop="goToChannel(mainChannelInfo.id)"
            >
              {{ mainChannelInfo.name }}
            </span>
          </div>

          <!-- 悬浮模态框 -->
          <div 
            v-if="hasActors"
            class="channel-popup opacity-0 invisible group-hover:opacity-100 group-hover:visible absolute left-0 bottom-full mb-2 bg-[#282828] rounded-lg shadow-lg transition-all duration-200 z-50 w-max max-w-[300px] p-3"
          >
            <!-- 主频道信息 -->
            <div class="flex items-center mb-2">
              <img 
                :src="mainChannelInfo.avatar" 
                alt="Channel Avatar" 
                class="w-8 h-8 rounded-full mr-2 object-cover"
                referrerpolicy="no-referrer"
              >
              <div class="flex flex-col">
                <span class="text-white text-sm font-medium">{{ mainChannelInfo.name }}</span>
                <span class="text-gray-400 text-xs">主频道</span>
              </div>
            </div>
            
            <!-- 分割线 -->
            <div class="h-[1px] bg-gray-700 my-2"></div>
            
            <!-- 演员列表 -->
            <div class="flex flex-col gap-2">
              <div 
                v-for="actor in actorChannels" 
                :key="actor.id"
                class="flex items-center group/actor cursor-pointer hover:bg-gray-700/50 p-1 rounded-lg transition-colors duration-150"
                @click.stop="goToChannel(actor.id)"
              >
                <img 
                  :src="actor.avatar" 
                  alt="Actor Avatar" 
                  class="w-6 h-6 rounded-full mr-2 object-cover"
                  referrerpolicy="no-referrer"
                >
                <span class="text-gray-300 group-hover/actor:text-white transition-colors duration-150">
                  {{ actor.name }}
                </span>
              </div>
            </div>
            
            <!-- 小三角形 -->
            <div class="absolute -bottom-2 left-4 w-4 h-4 bg-[#282828] transform rotate-45"></div>
          </div>
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
import { defineProps, defineEmits, onMounted, onUnmounted, ref, nextTick, inject, computed } from 'vue';
import ContextMenu from './ContextMenu.vue';
import useOptionsMenu from "../composables/useOptionsMenu.js";

const props = defineProps({
  video: {
    type: Object,
    required: true,
  },
  showAvatar: {
    type: Boolean,
    default: true
  },
  isChannelPage: Boolean,
  setVideoRef: Function,
  refreshContent: Function,
  isSelected: Boolean,
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

// 修改算属性来处理逗号分隔的字符串
const mainChannelInfo = computed(() => {
  const ids = props.video.channel_id?.toString().split(',') || [];
  const names = props.video.channel_name?.toString().split(',') || [];
  const avatars = props.video.channel_avatar?.toString().split(',') || [];
  
  return {
    id: ids[0] || '',
    name: names[0] || '',
    avatar: avatars[0] || '',
  };
});

const actorChannels = computed(() => {
  const ids = props.video.channel_id?.toString().split(',') || [];
  const names = props.video.channel_name?.toString().split(',') || [];
  const avatars = props.video.channel_avatar?.toString().split(',') || [];
  
  // 跳过第一个元素（主频道），处理剩余的演员信息
  return ids.slice(1).map((id, index) => ({
    id: id.trim(),
    name: names[index + 1]?.trim() || '',
    avatar: avatars[index + 1]?.trim() || '',
  })).filter(actor => actor.id && actor.name); // 过滤掉无效的数据
});

const hasActors = computed(() => actorChannels.value.length > 0);

// 修改 goToChannel 方法以接收 channel_id 参数
const goToChannel = (channelId) => {
  emit('goToChannel', channelId);
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

/* 添加新的样式 */
.gap-1 {
  gap: 0.25rem;
}

.leading-3 {
  line-height: 0.75rem;
}

/* 添加新的样式 */
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
</style>
