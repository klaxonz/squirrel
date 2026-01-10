<template>
  <div class="search-bar w-full p-4 bg-bg-primary">
    <div class="relative flex items-center w-full max-w-2xl mx-auto">
      <input
        v-model="searchQuery"
        @keyup.enter="handleSearch"
        type="text"
        placeholder="搜索"
        class="w-full h-10 pl-10 pr-4 text-sm bg-bg-elevated border border-border-secondary rounded-full focus:outline-none focus:border-color-info text-text-primary placeholder-text-muted"
      >
        <button
          @click="handleSearch"
          class="absolute left-3 top-1/2 transform -translate-y-1/2 focus:outline-none"
        >
          <MagnifyingGlassIcon class="h-5 w-5 text-text-muted" />
        </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { MagnifyingGlassIcon } from '@heroicons/vue/24/outline';

const searchQuery = ref('');
const emit = defineEmits(['search']);

const handleSearch = () => {
  emit('search', searchQuery.value);
};
</script>

<style scoped></style>
