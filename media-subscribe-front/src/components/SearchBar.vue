<template>
  <div class="search-bar bg-gray-100 px-4 py-2">
    <div class="relative">
      <input
        v-model="searchQuery"
        @keyup.enter="handleSearch"
        type="text"
        placeholder="搜索视频..."
        class="w-full h-9 px-4 pr-10 text-sm bg-gray-200 border-none rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-300"
      >
      <button
        @click="handleSearch"
        class="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-700 focus:outline-none"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const searchQuery = ref('');
const isScrollingUp = ref(false);

const handleSearch = () => {
  // Emit search event to parent component
  emit('search', searchQuery.value);
};

const clearSearch = () => {
  searchQuery.value = '';
  handleSearch();
};

// Expose isScrollingUp to parent component
defineExpose({ isScrollingUp });

// Define emits
const emit = defineEmits(['search']);
</script>

<style scoped>
.search-bar {
  @apply sticky top-0 z-20;
}
</style>