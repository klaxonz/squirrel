<template>
  <div class="tab-container mb-4">
    <div class="flex space-x-1">
      <button 
        v-for="tab in tabs" 
        :key="tab.value" 
        @click="$emit('update:modelValue', tab.value)"
        :class="['px-3 py-1.5 text-xs font-medium rounded-full transition-colors duration-150 ease-in-out', 
                 modelValue === tab.value ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-600 hover:bg-gray-200']"
      >
        {{ tab.label }}
        <span v-if="tab.count !== undefined" class="ml-1 bg-blue-200 text-blue-800 rounded-full px-1.5 py-0.5 text-2xs">
          {{ tab.count }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

const props = defineProps({
  modelValue: String,
  tabs: Array
});

defineEmits(['update:modelValue']);
</script>

<style scoped>
.tab-container {
  @apply overflow-x-auto whitespace-nowrap overscroll-contain overflow-touch;
}

.text-2xs {
  @apply text-[10px] leading-[14px];
}
</style>