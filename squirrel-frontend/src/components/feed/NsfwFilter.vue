<template>
  <div class="relative inline-block" ref="rootRef">
    <button
      @click="toggle"
      class="flex items-center flex-nowrap px-2 py-1.5 text-text-accent hover:bg-bg-elevated rounded-full transition-colors duration-150 border border-transparent"
      :class="[{ 'bg-bg-elevated border-border-primary': isOpen }, isMobile ? 'p-1.5' : 'space-x-1 px-2 text-xs']"
    >
      <!-- Shield icon -->
      <ShieldCheckIcon class="h-4 w-4" />
      <span v-if="!isMobile">敏感内容</span>
      <span v-if="!isMobile" class="opacity-70">· {{ currentLabel }}</span>
      <ChevronDownIcon
        class="transition-transform duration-200"
        :class="[
          isMobile ? 'h-2.5 w-2.5 -mr-0.5' : 'h-3 w-3',
          { 'transform rotate-180': isOpen }
        ]"
      />
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 mt-1 py-1 w-max min-w-full bg-bg-card rounded-lg shadow-lg z-50 animate-fade-in border border-border-primary"
    >
      <button
        v-for="option in nsfwOptions"
        :key="option.value"
        @click="selectOption(option.value)"
        class="w-full px-3 py-1.5 text-xs text-text-accent hover:bg-bg-elevated flex items-center gap-2"
      >
        <span class="flex-1 truncate">{{ option.label }}</span>
        <CheckIcon
          v-if="modelValue === option.value"
          class="h-3 w-3 text-color-info flex-shrink-0"
        />
        <span v-else class="h-3 w-3 flex-shrink-0"></span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { isMobile } from '@/composables/useMobile';
import { useDropdown } from '@/composables/useDropdown';
import {
  ShieldCheckIcon,
  ChevronDownIcon,
  CheckIcon
} from '@heroicons/vue/24/outline';

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
