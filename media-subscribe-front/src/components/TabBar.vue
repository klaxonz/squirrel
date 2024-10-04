<template>
  <div class="tab-bar flex space-x-2">
    <button
      v-for="tab in tabs"
      :key="tab.value"
      @click="$emit('update:modelValue', tab.value)"
      :class="['px-3 py-1 text-xs font-medium transition-colors duration-150 ease-in-out border-b-2', 
               modelValue === tab.value ? 'border-gray-900 text-gray-900' : 'border-transparent text-gray-600 hover:text-gray-900']"
    >
      {{ tab.label }}
      <span v-if="tab.count !== undefined" class="ml-1 bg-gray-200 text-gray-700 rounded-full px-1.5 py-0.5 text-xxs">
        {{ tab.count }}
      </span>
    </button>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

defineProps({
  modelValue: String,
  tabs: Array
});

defineEmits(['update:modelValue']);
</script>

<style scoped>
.text-xxs {
  font-size: 0.625rem;
  line-height: 0.75rem;
}
</style>