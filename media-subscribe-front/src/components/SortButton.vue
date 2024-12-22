<template>
  <div class="relative inline-block">
    <button
      @click="toggleDropdown"
      class="flex items-center space-x-1 px-2 py-1.5 text-xs text-[#f1f1f1] hover:bg-[#272727] rounded-full transition-colors duration-150"
      :class="{ 'bg-[#272727]': isOpen }"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
        <path d="M3 3a1 1 0 000 2h11a1 1 0 100-2H3zM3 7a1 1 0 000 2h7a1 1 0 100-2H3zM3 11a1 1 0 100 2h4a1 1 0 100-2H3z" />
      </svg>
      <span>排序方式</span>
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        class="h-3 w-3 transition-transform duration-200"
        :class="{ 'transform rotate-180': isOpen }"
        viewBox="0 0 20 20" 
        fill="currentColor"
      >
        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
      </svg>
    </button>

    <div
      v-if="isOpen"
      class="absolute mt-1 py-0.5 w-24 bg-[#282828] rounded-lg shadow-lg z-50 animate-fade-in"
    >
      <button
        v-for="option in sortOptions"
        :key="option.value"
        @click="selectOption(option.value)"
        class="w-full px-2 py-1.5 text-xs text-left text-[#f1f1f1] hover:bg-[#3f3f3f] flex items-center space-x-1"
      >
        <svg 
          v-if="modelValue === option.value"
          xmlns="http://www.w3.org/2000/svg" 
          class="h-3 w-3 text-[#3ea6ff] flex-shrink-0" 
          viewBox="0 0 20 20" 
          fill="currentColor"
        >
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
        <span v-else class="w-3 flex-shrink-0"></span>
        <span class="truncate">{{ option.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  modelValue: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:modelValue']);

const isOpen = ref(false);

const sortOptions = [
  { value: 'uploaded_at', label: '上传时间' },
  { value: 'created_at', label: '添加时间' }
];

const toggleDropdown = () => {
  isOpen.value = !isOpen.value;
};

const selectOption = (value) => {
  emit('update:modelValue', value);
  isOpen.value = false;
};

const handleClickOutside = (event) => {
  if (!event.target.closest('.relative')) {
    isOpen.value = false;
  }
};

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.animate-fade-in {
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style> 