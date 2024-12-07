<template>
  <div class="tab-bar flex items-center justify-between overflow-x-auto">
    <!-- 左侧标签 -->
    <div class="flex space-x-1">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        @click="$emit('update:modelValue', tab.value)"
        @dblclick="$emit('tab-dblclick', tab.value)"
        :class="[
          'px-3 py-1 text-xs font-medium rounded-full transition-colors duration-150 ease-in-out flex items-center',
          modelValue === tab.value
            ? 'bg-[#272727] text-white'
            : 'bg-[#0f0f0f] text-[#f1f1f1] hover:bg-[#272727]'
        ]"
      >
        {{ tab.label }}
        <span
          v-if="tab.count !== undefined"
          :class="[
            'ml-1 text-[10px]',
            modelValue === tab.value
              ? 'text-white'
              : 'text-[#aaaaaa]'
          ]"
        >
          {{ tab.count }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { defineProps, defineEmits } from 'vue';

defineProps({
  modelValue: String,
  tabs: Array
});

defineEmits(['update:modelValue', 'tab-dblclick']);
</script>

<style scoped>
.tab-bar {
  scrollbar-width: none;
  -ms-overflow-style: none;
  background-color: #0f0f0f;
}

.tab-bar::-webkit-scrollbar {
  display: none;
}

button {
  white-space: nowrap;
}
</style>
