<template>
  <div :class="['search-bar', { 'hidden': isScrollingUp }]" ref="searchBar">
    <div class="flex items-center w-11/12 mx-auto relative ">
      <input
        v-model="searchQuery"
        @keyup.enter="handleSearch"
        type="text"
        placeholder="搜索视频..."
        class="search-input flex-grow h-7 px-3 pr-8 text-xs border border-gray-300 rounded-l-md focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:ring-opacity-50 transition duration-200"
      >
      <button
        v-if="searchQuery"
        @click="clearSearch"
        class="clear-button absolute right-16 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 focus:outline-none"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"/>
        </svg>
      </button>
      <button
        @click="handleSearch"
        class="search-button h-7 px-3 text-xs font-medium bg-blue-500 text-white rounded-r-md hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-400 focus:ring-opacity-50 focus:ring-offset-2 transition duration-200"
      >
        搜索
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
  position: sticky;
  top: 0;
  background-color: white;
  z-index: 10;
  padding: 0.25rem;
  transition: transform 0.3s ease-in-out;
}

.search-bar.hidden {
  transform: translateY(-100%);
}

.search-input {
  border-right: none;
  border-radius: 9999px 0 0 9999px;
}

.clear-button {
  right: 2rem;
}

.search-button {
  border-left: none;
  border-radius: 0 9999px 9999px 0;
}

.search-bar input:focus,
.search-bar button:focus {
  box-shadow: 0 0 0 0 rgba(111, 164, 248, 0.5);
}
</style>