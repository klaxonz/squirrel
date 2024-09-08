<template>
  <div
    class="options-menu fixed bg-white shadow-lg rounded-lg py-2 z-50 w-48"
    :style="{ top: position.top + 'px', left: position.left + 'px' }"
    @click.stop
  >
    <button @click="$emit('toggleReadStatus', true)" class="option-item">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
      </svg>
      标记为已读
    </button>
    <button @click="$emit('toggleReadStatus', false)" class="option-item">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
      </svg>
      标记为未读
    </button>
    <button @click="$emit('markReadBatch', 'above')" class="option-item">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 10l7-7m0 0l7 7m-7-7v18" />
      </svg>
      以上标记为已读
    </button>
    <button @click="$emit('markReadBatch', 'below')" class="option-item">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 14l-7 7m0 0l-7-7m7 7V3" />
      </svg>
      以下标记为已读
    </button>
    <button @click="$emit('downloadVideo')" class="option-item">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
      下载
    </button>
    <button @click="$emit('copyVideoLink')" class="option-item">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-2.5" />
      </svg>
      复制链接
    </button>
    <button @click="$emit('dislikeVideo')" class="option-item">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.76.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
      </svg>
      不喜欢
    </button>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

defineProps({
  position: {
    type: Object,
    required: true
  }
});

defineEmits([
  'toggleReadStatus',
  'markReadBatch',
  'downloadVideo',
  'copyVideoLink',
  'dislikeVideo'
]);
</script>

<style scoped>
.options-menu {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
}

.option-item {
  @apply flex items-center w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition-colors duration-150 ease-in-out;
}

.option-item:first-child {
  @apply rounded-t-lg;
}

.option-item:last-child {
  @apply rounded-b-lg;
}

.option-item:hover {
  @apply bg-blue-50 text-blue-600;
}

.option-item svg {
  @apply text-gray-400 group-hover:text-blue-500 transition-colors duration-150 ease-in-out;
}
</style>