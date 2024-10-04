<template>
  <div class="search-bar flex items-center w-full max-w-2xl mx-auto">
    <input
      v-model="searchQuery"
      @keyup.enter="handleSearch"
      type="text"
      placeholder="搜索"
      class="w-full h-8 px-4 text-sm bg-white border border-gray-300 rounded-l-full focus:outline-none focus:border-blue-500"
    >
    <button
      @click="handleSearch"
      class="h-8 px-4 bg-gray-100 border border-l-0 border-gray-300 rounded-r-full hover:bg-gray-200 focus:outline-none"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 text-gray-600" viewBox="0 0 20 20" fill="currentColor">
        <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
      </svg>
    </button>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const searchQuery = ref('');
const emit = defineEmits(['search']);

const handleSearch = () => {
  emit('search', searchQuery.value);
};
</script>