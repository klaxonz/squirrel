<template>
  <div class="relative inline-block" ref="rootRef">
    <button
      @click="toggle"
      class="flex items-center px-2 py-1.5 text-[#f1f1f1] hover:bg-[#272727] rounded-full transition-colors duration-150"
      :class="[{ 'bg-[#272727]': isOpen }, isMobile ? 'p-1.5' : 'space-x-1 px-2 text-xs']"
    >
      <!-- Shield icon -->
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2l7 3v6c0 5.55-3.84 10.74-7 12-3.16-1.26-7-6.45-7-12V5l7-3z"/>
      </svg>
      <span v-if="!isMobile">敏感内容</span>
      <span v-if="!isMobile" class="opacity-70">· {{ currentLabel }}</span>
      <svg 
        xmlns="http://www.w3.org/2000/svg" 
        class="transition-transform duration-200"
        :class="[
          isMobile ? 'h-2.5 w-2.5 -mr-0.5' : 'h-3 w-3',
          { 'transform rotate-180': isOpen }
        ]"
        viewBox="0 0 20 20" 
        fill="currentColor"
      >
        <path fill-rule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clip-rule="evenodd" />
      </svg>
    </button>

    <div
      v-if="isOpen"
      class="absolute mt-1 py-0.5 w-28 bg-[#282828] rounded-lg shadow-lg z-50 animate-fade-in"
      :class="{
        'right-0': isMobile,
        'left-0': !isMobile
      }"
      :style="isMobile ? { right: '0', left: 'auto' } : {}"
    >
      <button
        v-for="option in nsfwOptions"
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
import { computed } from 'vue';
import { isMobile } from "../composables/useMobile.js";
import { useDropdown } from "../composables/useDropdown.js";

const props = defineProps({
  modelValue: {
    type: String,
    required: true
  }
});

const emit = defineEmits(['update:modelValue']);

const { isOpen, rootRef, toggle, close } = useDropdown();

const nsfwOptions = [
  { value: 'all', label: '全部' },
  { value: 'yes', label: '仅NSFW' },
  { value: 'no', label: '仅非NSFW' }
];

const currentLabel = computed(() => nsfwOptions.find(o => o.value === props.modelValue)?.label || '全部');

const selectOption = (value) => {
  emit('update:modelValue', value);
  close();
};
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

