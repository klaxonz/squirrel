<template>
  <div class="tab-container bg-white shadow-sm mb-1">
    <div class="flex justify-around">
      <button 
        v-for="tab in tabs" 
        :key="tab.value" 
        @click="$emit('update:modelValue', tab.value)"
        :class="['px-4 py-2 text-sm font-medium', modelValue === tab.value ? 'text-blue-600 border-b-2 border-blue-600' : 'text-gray-500']"
      >
        {{ tab.label }}
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
</style>