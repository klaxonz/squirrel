<template>
  <div class="global-search-bar bg-background px-4 py-3">
    <div class="max-w-2xl mx-auto">
      <div class="relative flex items-center w-full">
        <input
          v-model="inputValue"
          @keyup.enter="handleSearch"
          @keyup.esc="clearSearch"
          @input="handleInput"
          type="text"
          :placeholder="placeholder"
          class="w-full h-10 pl-10 pr-12 text-sm bg-card border border-border rounded-full focus:outline-none focus:border-border text-foreground placeholder:text-muted-foreground transition-colors"
        >
        <button
          @click="handleSearch"
          class="absolute left-3 top-1/2 transform -translate-y-1/2 focus:outline-none"
        >
          <MagnifyingGlassIcon class="h-5 w-5 text-muted-foreground" />
        </button>


        <!-- 清除按钮 -->
        <button
          v-if="inputValue"
          @click="clearSearch"
          title="清除搜索 (ESC)"
          class="absolute right-3 top-1/2 transform -translate-y-1/2 focus:outline-none hover:text-foreground hover:bg-accent text-muted-foreground rounded-full p-1 transition-colors"
        >
          <XMarkIcon class="h-4 w-4" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { MagnifyingGlassIcon, XMarkIcon } from '@heroicons/vue/24/outline';

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
input:focus {
  box-shadow: 0 0 0 2px hsl(var(--border));
}
</style>
