<template>
  <div 
    v-if="isOpen"
    class="context-menu fixed bg-bg-card border border-border-primary shadow-xl rounded-lg py-2 z-50 w-56 overflow-visible transition-all duration-200 ease-in-out"
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
            <CheckIcon class="h-5 w-5 mr-3 text-text-muted group-hover:text-text-primary transition-colors duration-150" />
            <span class="text-text-primary group-hover:text-text-primary transition-colors duration-150">标记为已读</span>
          </span>
          <ChevronRightIcon class="h-4 w-4 text-text-muted group-hover:text-text-primary transition-colors duration-150" />
        </button>
        <div v-show="showReadMenu" class="submenu absolute left-full top-0 ml-2 w-48 bg-bg-card border border-border-primary shadow-lg rounded-lg overflow-hidden">
          <button @click.stop="$emit('toggleReadStatus', true)" class="sub-option-item">
            <span class="mr-2">✓</span>此项
          </button>
        </div>
      </div>
      <div class="relative group" 
           @mouseenter="showUnreadMenu = true" 
           @mouseleave="showUnreadMenu = false"
           @click.stop="toggleUnreadMenu">
        <button class="option-item w-full flex justify-between items-center group">
          <span class="flex items-center">
            <XMarkIcon class="h-5 w-5 mr-3 text-text-muted group-hover:text-text-primary transition-colors duration-150" />
            <span class="text-text-primary group-hover:text-text-primary transition-colors duration-150">标记为未读</span>
          </span>
          <ChevronRightIcon class="h-4 w-4 text-text-muted group-hover:text-text-primary transition-colors duration-150" />
        </button>
        <div v-if="showUnreadMenu" class="submenu absolute left-full top-0 ml-2 w-48 bg-bg-card border border-border-primary shadow-lg rounded-lg overflow-hidden">
          <button @click.stop="$emit('toggleReadStatus', false)" class="sub-option-item">
            <span class="mr-2">✓</span>此项
          </button>
        </div>
      </div>
    </div>
    <div class="border-t border-border-primary my-1"></div>
    <div class="py-1">
      <button @click="handleLiked" class="option-item group">
        <HeartIcon v-if="video.is_liked === 1"
             class="h-5 w-5 mr-3 text-color-error"
             fill="currentColor" />

        <HandThumbDownIcon v-else-if="video.is_liked === 0"
             class="h-5 w-5 mr-3 text-color-warning" />

        <HeartIcon v-else
             class="h-5 w-5 mr-3 text-text-muted group-hover:text-text-primary transition-colors duration-150" />

        <span class="text-text-primary group-hover:text-text-primary transition-colors duration-150">
          {{ 
            video.is_liked === 1 ? '已喜欢' : 
            video.is_liked === 0 ? '不喜欢' : 
            '喜欢'
          }}
        </span>
      </button>
      <button @click="$emit('copyVideoLink')" class="option-item group">
        <ClipboardDocumentIcon class="h-5 w-5 mr-3 text-text-muted group-hover:text-text-primary transition-colors duration-150" />
        <span class="text-text-primary group-hover:text-text-primary transition-colors duration-150">复制链接</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import {
  CheckIcon,
  ChevronRightIcon,
  XMarkIcon,
  HeartIcon,
  HandThumbDownIcon,
  ClipboardDocumentIcon
} from '@heroicons/vue/24/outline';

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
  'copyVideoLink',
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
  box-shadow: var(--shadow-popover);
  animation: fadeIn 0.2s ease-out;
}

.option-item {
  @apply flex items-center w-full px-3 py-2 text-sm font-medium transition-colors duration-150 ease-in-out;
}

.sub-option-item {
  @apply w-full px-3 py-2 text-sm font-normal text-text-primary hover:bg-bg-elevated transition-colors duration-150 ease-in-out flex items-center;
}

.option-item:hover {
  @apply bg-bg-elevated;
}

.submenu {
  animation: slideIn 0.2s ease-out;
  box-shadow: var(--shadow-popover);
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
