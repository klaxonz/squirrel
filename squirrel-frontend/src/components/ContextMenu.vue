<template>
  <div 
    v-if="isOpen"
    class="context-menu fixed bg-[#282828] shadow-xl rounded-lg py-2 z-50 w-56 overflow-visible transition-all duration-200 ease-in-out"
    :style="{ top: `${position.y}px`, left: `${position.x}px` }"
    @click.stop
  >
    <div class="py-1">
      <div class="relative group"
           @mouseenter="showReadMenu = true" 
           @mouseleave="showReadMenu = false"
           @click.stop="toggleReadMenu">
        <button class="option-item w-full flex justify-between items-center group">
          <span class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3 text-[#aaaaaa] group-hover:text-white transition-colors duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
            </svg>
            <span class="text-[#ffffff] group-hover:text-white transition-colors duration-150">标记为已读</span>
          </span>
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-[#aaaaaa] group-hover:text-white transition-colors duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
        <div v-show="showReadMenu" class="submenu absolute left-full top-0 ml-2 w-48 bg-[#282828] shadow-lg rounded-lg overflow-hidden">
          <button @click.stop="$emit('toggleReadStatus', true)" class="sub-option-item">
            <span class="mr-2">✓</span>此项
          </button>
          <button @click.stop="$emit('markReadBatch', true, 'above')" class="sub-option-item">
            <span class="mr-2">↑</span>以上
          </button>
          <button @click.stop="$emit('markReadBatch', true, 'below')" class="sub-option-item">
            <span class="mr-2">↓</span>以下
          </button>
        </div>
      </div>
      <div class="relative group" 
           @mouseenter="showUnreadMenu = true" 
           @mouseleave="showUnreadMenu = false"
           @click.stop="toggleUnreadMenu">
        <button class="option-item w-full flex justify-between items-center group">
          <span class="flex items-center">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3 text-[#aaaaaa] group-hover:text-white transition-colors duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
            <span class="text-[#ffffff] group-hover:text-white transition-colors duration-150">标记为未读</span>
          </span>
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-[#aaaaaa] group-hover:text-white transition-colors duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </button>
        <div v-if="showUnreadMenu" class="submenu absolute left-full top-0 ml-2 w-48 bg-[#282828] shadow-lg rounded-lg overflow-hidden">
          <button @click.stop="$emit('toggleReadStatus', false)" class="sub-option-item">
            <span class="mr-2">✓</span>此项
          </button>
          <button @click.stop="$emit('markReadBatch', false, 'above')" class="sub-option-item">
            <span class="mr-2">↑</span>以上
          </button>
          <button @click.stop="$emit('markReadBatch', false, 'below')" class="sub-option-item">
            <span class="mr-2">↓</span>以下
          </button>
        </div>
      </div>
    </div>
    <div class="border-t border-[#3f3f3f] my-1"></div>
    <div class="py-1">
      <button @click="handleLiked" class="option-item group">
        <svg v-if="video.is_liked === 1"
             xmlns="http://www.w3.org/2000/svg" 
             class="h-5 w-5 mr-3 text-red-500" 
             fill="currentColor"
             viewBox="0 0 24 24" 
        >
          <path d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>

        <svg v-else-if="video.is_liked === 0"
             xmlns="http://www.w3.org/2000/svg" 
             class="h-5 w-5 mr-3 text-yellow-500" 
             fill="none"
             viewBox="0 0 24 24" 
             stroke="currentColor"
        >
          <path stroke-linecap="round" 
                stroke-linejoin="round" 
                stroke-width="2" 
                d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
        </svg>

        <svg v-else
             xmlns="http://www.w3.org/2000/svg" 
             class="h-5 w-5 mr-3 text-[#aaaaaa] group-hover:text-white transition-colors duration-150" 
             fill="none"
             viewBox="0 0 24 24" 
             stroke="currentColor"
        >
          <path stroke-linecap="round" 
                stroke-linejoin="round" 
                stroke-width="2" 
                d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
        </svg>

        <span class="text-[#ffffff] group-hover:text-white transition-colors duration-150">
          {{ 
            video.is_liked === 1 ? '已喜欢' : 
            video.is_liked === 0 ? '不喜欢' : 
            '喜欢'
          }}
        </span>
      </button>
      <button @click="handleDownload" class="option-item group">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3 text-[#aaaaaa] group-hover:text-white transition-colors duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
        </svg>
        <span class="text-[#ffffff] group-hover:text-white transition-colors duration-150">下载视频</span>
      </button>
      <button @click="$emit('copyVideoLink')" class="option-item group">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-3 text-[#aaaaaa] group-hover:text-white transition-colors duration-150" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-2.5" />
        </svg>
        <span class="text-[#ffffff] group-hover:text-white transition-colors duration-150">复制链接</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue';
import { createApp } from 'vue';
import Toast from './Toast.vue';

const props = defineProps({
  position: {
    type: Object,
    required: true
  },
  isOpen: {
    type: Boolean,
    required: true
  },
  isRead: {
    type: Boolean,
    default: false
  },
  video: {
    type: Object,
    required: true
  }
});

const emit = defineEmits([
  'close',
  'toggleReadStatus',
  'dislikeVideo',
  'downloadVideo',
  'copyVideoLink',
  'markReadBatch',
  'toggleLike'
]);

const showReadMenu = ref(false);
const showUnreadMenu = ref(false);

const toggleReadMenu = (event) => {
  event.stopPropagation();
  showReadMenu.value = !showReadMenu.value;
  showUnreadMenu.value = false;
};

const toggleUnreadMenu = (event) => {
  event.stopPropagation();
  showUnreadMenu.value = !showUnreadMenu.value;
  showReadMenu.value = false;
};

const handleClickOutside = (event) => {
  if (!event.target.closest('.context-menu')) {
    emit('close');
    showReadMenu.value = false;
    showUnreadMenu.value = false;
  }
};

const showToast = (message, type = 'success') => {
  const toast = createApp(Toast, {
    message,
    type,
    duration: 3000,
  });
  const mountNode = document.createElement('div');
  document.body.appendChild(mountNode);
  toast.mount(mountNode);
  
  setTimeout(() => {
    document.body.removeChild(mountNode);
  }, 3000);
};

const handleDownload = async () => {
  try {
    emit('downloadVideo', props.video);
    showToast('已添加到下载队列');
    emit('close');
  } catch (error) {
    showToast('添加下载任务失败', 'error');
  }
};

const handleLiked = async () => {
  await emit('toggleLike', props.video);
  await emit('close');
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.context-menu {
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
  animation: fadeIn 0.2s ease-out;
}

.option-item {
  @apply flex items-center w-full px-3 py-2 text-sm font-medium transition-colors duration-150 ease-in-out;
}

.sub-option-item {
  @apply w-full px-3 py-2 text-sm font-normal text-[#ffffff] hover:bg-[#3f3f3f] transition-colors duration-150 ease-in-out flex items-center;
}

.option-item:hover {
  @apply bg-[#3f3f3f];
}

.submenu {
  animation: slideIn 0.2s ease-out;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
}

@keyframes fadeIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

@keyframes slideIn {
  from { opacity: 0; transform: translateX(-10px); }
  to { opacity: 1; transform: translateX(0); }
}

.context-menu {
  position: fixed;
}

.submenu {
  position: absolute;
  left: 100%;
  top: 0;
  z-index: 60;
}
</style>
