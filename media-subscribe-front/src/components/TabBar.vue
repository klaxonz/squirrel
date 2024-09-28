<template>
  <div class="tab-container mb-4 bg-white">
    <div class="flex space-x-2 px-4 py-2 overflow-x-auto">
      <button 
        v-for="tab in tabs" 
        :key="tab.value" 
        @click="$emit('update:modelValue', tab.value)"
        :class="['px-3 py-1.5 text-sm font-medium rounded-full transition-colors duration-150 ease-in-out', 
                 modelValue === tab.value ? 'bg-gray-200 text-gray-900' : 'text-gray-600 hover:bg-gray-100']"
      >
        {{ tab.label }}
        <span v-if="tab.count !== undefined" class="ml-1 bg-gray-300 text-gray-800 rounded-full px-1.5 py-0.5 text-xs">
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
  @apply sticky top-0 z-10 border-b border-gray-200;
}

.text-xs {
  font-size: 0.75rem;
  line-height: 1rem;
}
</style>