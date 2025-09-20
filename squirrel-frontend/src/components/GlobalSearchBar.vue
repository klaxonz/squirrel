<template>
  <div class="global-search-bar bg-[#0f0f0f] border-[#272727] px-4 py-3">
    <div class="max-w-2xl mx-auto">
      <div class="relative flex items-center w-full">
        <input
          v-model="inputValue"
          @keyup.enter="handleSearch"
          @keyup.esc="clearSearch"
          @input="handleInput"
          type="text"
          :placeholder="placeholder"
          class="w-full h-10 pl-10 pr-12 text-sm bg-[#222222] border border-[#303030] rounded-full focus:outline-none focus:border-[#4a4a4c] text-white placeholder-gray-400"
        >
        <button
          @click="handleSearch"
          class="absolute left-3 top-1/2 transform -translate-y-1/2 focus:outline-none"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 text-gray-400" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
          </svg>
        </button>
        
        <!-- 清除按钮 -->
        <button
          v-if="searchQuery"
          @click="clearSearch"
          title="清除搜索 (ESC)"
          class="absolute right-3 top-1/2 transform -translate-y-1/2 focus:outline-none hover:text-white hover:bg-white/10 text-gray-400 rounded-full p-1 transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
            <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue';

// Props: presentational component only
const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  placeholder: {
    type: String,
    default: '搜索...'
  },
  debounceMs: {
    type: Number,
    default: 300
  }
});

const emit = defineEmits(['update:modelValue', 'search', 'clear']);

const inputValue = ref(props.modelValue);

watch(() => props.modelValue, (val) => {
  if (val !== inputValue.value) {
    inputValue.value = val || '';
  }
});

let searchTimeout = null;
const handleInput = () => {
  emit('update:modelValue', inputValue.value);
  if (searchTimeout) clearTimeout(searchTimeout);
  searchTimeout = setTimeout(() => {
    emit('search');
  }, props.debounceMs);
};

const handleSearch = () => {
  emit('search');
};

const clearSearch = () => {
  inputValue.value = '';
  emit('update:modelValue', '');
  emit('clear');
};

// Expose helpers
defineExpose({
  focus: () => {
    const input = document.querySelector('.global-search-bar input');
    if (input) input.focus();
  },
  clear: clearSearch,
  setQuery: (query) => {
    inputValue.value = query || '';
    emit('update:modelValue', inputValue.value);
  }
});
</script>

<style scoped>
.global-search-bar {
  /* 确保搜索框在最顶层 */
  z-index: 10;
}

/* 添加平滑过渡效果 */
input {
  transition: border-color 0.2s ease-in-out;
}

input:focus {
  box-shadow: 0 0 0 2px rgba(74, 74, 76, 0.3);
}
</style>
