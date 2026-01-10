<template>
  <div class="relative inline-block" ref="rootRef">
    <button
      @click="toggle"
      class="flex items-center flex-nowrap px-2 py-1.5 text-text-accent hover:bg-bg-elevated rounded-full transition-colors duration-150 border border-transparent"
      :class="[{ 'bg-bg-elevated border-border-primary': isOpen }, isMobile ? 'p-1.5' : 'space-x-1 px-2 text-xs']"
    >
      <Bars4Icon class="h-4 w-4" />
      <span v-if="!isMobile">站点</span>
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
      class="absolute mt-1 py-0.5 w-40 bg-bg-card rounded-lg shadow-lg z-50 animate-fade-in border border-border-primary"
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
        class="w-full px-2 py-1.5 text-xs text-left text-text-accent hover:bg-bg-elevated flex items-center space-x-1"
      >
        <CheckIcon
          v-if="modelValue === opt.value"
          class="h-3 w-3 text-color-info flex-shrink-0"
        />
        <span v-else class="w-3 flex-shrink-0"></span>
        <span class="truncate">{{ opt.label }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import {
  Bars4Icon,
  ChevronDownIcon,
  CheckIcon
} from '@heroicons/vue/24/outline';
import { isMobile } from "../composables/useMobile.js";
import { useDropdown } from "../composables/useDropdown.js";
import { useSites } from "../composables/useSites.js";

const props = defineProps({
  modelValue: {
    type: String,
    default: undefined
  }
});

const emit = defineEmits(['update:modelValue']);

const { isOpen, rootRef, toggle, close } = useDropdown();
const options = ref([{ value: undefined, label: '全部站点' }]);
const { options: cachedOptions, fetchSites } = useSites();

const currentLabel = computed(() => {
  const found = options.value.find(o => o.value === props.modelValue);
  return found ? found.label : options.value[0]?.label || '全部站点';
});

const selectOption = (value) => {
  emit('update:modelValue', value);
  close();
};
onMounted(async () => {
  if (cachedOptions.value) {
    options.value = cachedOptions.value;
  } else {
    const { data } = await fetchSites();
    if (data) options.value = data;
  }
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


