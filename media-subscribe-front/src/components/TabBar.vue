<template>
  <div class="tab-container bg-white shadow-sm mb-1">
    <div class="flex justify-around">
      <button 
        v-for="tab in tabs" 
        :key="tab.value" 
        @click="$emit('update:modelValue', tab.value)"
        :class="['px-3 py-1 text-xs font-medium flex items-center', modelValue === tab.value ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500']"
      >
        {{ tab.label }}
        <span v-if="tab.count !== undefined" class="ml-1 bg-gray-200 text-gray-700 rounded-full px-2 py-0.5 text-2xs">
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
  overflow-x: auto;
  white-space: nowrap;
  -webkit-overflow-scrolling: touch;
}

.tab-container button {
  height: 2rem; /* 32px */
  line-height: 1.75rem; /* 28px, to account for the border */
  transition: all 0.2s ease-in-out;
}

.tab-container button:hover {
  color: #3b82f6; /* text-blue-500 */
}

.text-2xs {
  font-size: 0.65rem;
  line-height: 0.75rem;
}
</style>