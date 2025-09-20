<template>
  <div class="relative inline-block">
    <button
      @click="toggleDropdown"
      class="flex items-center px-2 py-1.5 text-[#f1f1f1] hover:bg-[#272727] rounded-full transition-colors duration-150"
      :class="[{ 'bg-[#272727]': isOpen }, isMobile ? 'p-1.5' : 'space-x-1 px-2 text-xs']"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" viewBox="0 0 20 20" fill="currentColor">
        <path d="M3 5a2 2 0 012-2h10a2 2 0 012 2v0a2 2 0 01-2 2H5a2 2 0 01-2-2zM3 15a2 2 0 012-2h6a2 2 0 012 2v0a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
      </svg>
      <span v-if="!isMobile">站点</span>
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
      class="absolute mt-1 py-0.5 w-40 bg-[#282828] rounded-lg shadow-lg z-50 animate-fade-in"
      :class="{
        'right-0': isMobile,
        'left-0': !isMobile
      }"
      :style="isMobile ? { right: '0', left: 'auto' } : {}"
    >
      <button
        v-for="opt in options"
        :key="opt.value || 'all'"
        @click="selectOption(opt.value)"
        class="w-full px-2 py-1.5 text-xs text-left text-[#f1f1f1] hover:bg-[#3f3f3f] flex items-center space-x-1"
      >
        <svg 
          v-if="modelValue === opt.value"
          xmlns="http://www.w3.org/2000/svg" 
          class="h-3 w-3 text-[#3ea6ff] flex-shrink-0" 
          viewBox="0 0 20 20" 
          fill="currentColor"
        >
          <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
        </svg>
        <span v-else class="w-3 flex-shrink-0"></span>
        <span class="truncate">{{ opt.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { get } from '../utils/request';
import { isMobile } from "../composables/useMobile.js";

const props = defineProps({
  modelValue: {
    type: String,
    default: undefined
  }
});

const emit = defineEmits(['update:modelValue']);

const isOpen = ref(false);
const options = ref([{ value: undefined, label: '全部站点' }]);

const currentLabel = computed(() => {
  const found = options.value.find(o => o.value === props.modelValue);
  return found ? found.label : options.value[0]?.label || '全部站点';
});

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

onMounted(async () => {
  document.addEventListener('click', handleClickOutside);
  const { data } = await get('/api/sites');
  const items = data ? Object.entries(data) : [];
  const opts = [{ value: undefined, label: '全部站点' }];
  for (const [slug, info] of items) {
    if (info && info.enabled !== false) {
      opts.push({ value: slug, label: info.label || slug });
    }
  }
  options.value = opts;
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


