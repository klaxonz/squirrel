<template>
  <div
    class="tab-bar flex items-center justify-between overflow-x-auto"
    role="tablist"
    aria-label="Tabs"
    ref="containerRef"
    @keydown="onKeydown"
  >
    <!-- 左侧标签 -->
    <div class="flex space-x-1">
      <button
        v-for="(tab, index) in tabs"
        :key="tab.value"
        @click="$emit('update:modelValue', tab.value)"
        @dblclick="$emit('tab-dblclick', tab.value)"
        role="tab"
        :aria-selected="modelValue === tab.value"
        :tabindex="modelValue === tab.value ? 0 : -1"
        ref="tabRefs"
        :class="[
          'px-3 py-1 text-xs font-medium rounded-full transition-colors duration-150 ease-in-out flex items-center',
          modelValue === tab.value
            ? 'bg-bg-elevated text-text-primary'
            : 'bg-bg-primary text-text-accent hover:bg-bg-elevated'
        ]"
      >
        {{ tab.label }}
        <span
          v-if="tab.count !== undefined"
          :class="[
            'ml-1 text-2xs',
            modelValue === tab.value
              ? 'text-text-primary'
              : 'text-text-muted'
          ]"
        >
          {{ tab.count }}
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue';

const props = defineProps({
  modelValue: String,
  tabs: Array
});

const emit = defineEmits(['update:modelValue', 'tab-dblclick']);

const containerRef = ref(null);
const tabRefs = ref([]);

const currentIndex = computed(() => (props.tabs || []).findIndex(t => t.value === props.modelValue));

const focusTab = (idx) => {
  const el = tabRefs.value[idx];
  if (el && typeof el.focus === 'function') el.focus();
};

const setActiveByIndex = (idx) => {
  const tabs = props.tabs || [];
  if (idx >= 0 && idx < tabs.length) {
    emit('update:modelValue', tabs[idx].value);
    focusTab(idx);
  }
};

const onKeydown = (e) => {
  const tabs = props.tabs || [];
  if (!tabs.length) return;
  const idx = currentIndex.value >= 0 ? currentIndex.value : 0;
  switch (e.key) {
    case 'ArrowRight':
      e.preventDefault();
      setActiveByIndex((idx + 1) % tabs.length);
      break;
    case 'ArrowLeft':
      e.preventDefault();
      setActiveByIndex((idx - 1 + tabs.length) % tabs.length);
      break;
    case 'Home':
      e.preventDefault();
      setActiveByIndex(0);
      break;
    case 'End':
      e.preventDefault();
      setActiveByIndex(tabs.length - 1);
      break;
    case 'Enter':
    case ' ':
      // Already handled by update when focused tab changes; ensure click behavior
      e.preventDefault();
      setActiveByIndex(idx);
      break;
    default:
      break;
  }
};
</script>

<style scoped>
.tab-bar {
  scrollbar-width: none;
  -ms-overflow-style: none;
  background-color: var(--bg-primary);
}

.tab-bar::-webkit-scrollbar {
  display: none;
}

button {
  white-space: nowrap;
}
</style>
