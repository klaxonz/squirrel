<template>
  <div class="search-bar w-full p-4">
    <div class="relative flex items-center w-full max-w-2xl mx-auto">
      <input
        v-model="searchQuery"
        @keyup.enter="handleSearch"
        type="text"
        placeholder="搜索"
        class="w-full h-10 pl-10 pr-4 text-sm bg-[#222222] border border-[#303030] rounded-full focus:outline-none focus:border-[#4a4a4c] text-white placeholder-gray-400"
      >
      <button
        @click="handleSearch"
        class="absolute left-3 top-1/2 transform -translate-y-1/2 focus:outline-none"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
        </svg>
      </button>
    </div>
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

<style scoped>
.search-bar {
  background-color: #0f0f0f;
}
</style>
