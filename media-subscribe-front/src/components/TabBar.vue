<template>
  <div class="tab-bar flex items-center justify-between px-4 py-2 overflow-x-auto">
    <!-- 左侧标签 -->
    <div class="flex space-x-1">
      <button
        v-for="tab in tabs"
        :key="tab.value"
        @click="$emit('update:modelValue', tab.value)"
        :class="[
          'px-3 py-1 text-sm font-medium rounded-full transition-colors duration-150 ease-in-out flex items-center',
          modelValue === tab.value
            ? 'bg-[#272727] text-white'
            : 'bg-[#0f0f0f] text-[#f1f1f1] hover:bg-[#272727]'
        ]"
      >
        {{ tab.label }}
        <span
          v-if="tab.count !== undefined"
          :class="[
            'ml-1 px-1 text-xs',
            modelValue === tab.value
              ? 'text-white'
              : 'text-[#aaaaaa]'
          ]"
        >
          {{ tab.count }}
        </span>
      </button>
    </div>

    <!-- 右侧排序选项 -->
    <div class="flex items-center">
      <div class="relative">
        <select
          v-model="selectedSort"
          @change="$emit('sort-change', selectedSort)"
          class="appearance-none bg-transparent text-[#aaaaaa] text-xs py-1.5 pl-2 pr-6 rounded cursor-pointer
                 hover:bg-[#272727] focus:outline-none"
        >
          <option value="uploaded_at" class="bg-[#212121] text-[#f1f1f1]">上传时间</option>
          <option value="created_at" class="bg-[#212121] text-[#f1f1f1]">加入时间</option>
        </select>
        <div class="absolute right-1 top-1/2 transform -translate-y-1/2 pointer-events-none">
          <svg 
            class="w-3 h-3 text-[#aaaaaa]" 
            fill="none" 
            stroke="currentColor" 
            viewBox="0 0 24 24"
          >
            <path d="M19 9l-7 7-7-7" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue';

defineProps({
  modelValue: String,
  tabs: Array
});

const selectedSort = ref('uploaded_at');

defineEmits(['update:modelValue', 'sort-change']);
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

select {
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
}

select::-ms-expand {
  display: none;
}

select option {
  background-color: #212121;
  padding: 4px;
}
</style>
