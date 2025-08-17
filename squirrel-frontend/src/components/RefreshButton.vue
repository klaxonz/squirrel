<template>
  <button
    :class="['px-3 py-1 text-xs rounded-full bg-[#0f0f0f] text-[#f1f1f1] hover:bg-[#272727] flex items-center justify-center', customClass]"
    :title="title"
    :aria-label="ariaLabel || title"
    @click="$emit('click')"
  >
    <ArrowPathIcon :class="['h-4 w-4', { 'spin-anim': isSpinning }]" />
  </button>
</template>

<script setup>
import { ref, watch, onUnmounted } from 'vue';
import { ArrowPathIcon } from '@heroicons/vue/24/outline';

const props = defineProps({
  loading: { type: Boolean, default: false },
  minSpinMs: { type: Number, default: 800 },
  title: { type: String, default: '刷新' },
  ariaLabel: { type: String, default: '' },
  customClass: { type: String, default: '' },
});

defineEmits(['click']);

const isSpinning = ref(false);
let spinStartAt = 0;
let timer = null;

const clearTimer = () => {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
};

watch(() => props.loading, (val) => {
  if (val) {
    clearTimer();
    isSpinning.value = true;
    spinStartAt = Date.now();
  } else {
    const elapsed = Date.now() - spinStartAt;
    const remain = Math.max(0, props.minSpinMs - elapsed);
    clearTimer();
    timer = setTimeout(() => {
      isSpinning.value = false;
      clearTimer();
    }, remain);
  }
});

onUnmounted(() => {
  clearTimer();
});
</script>

<style scoped>
@keyframes spin { to { transform: rotate(360deg); } }
.spin-anim { animation: spin 0.8s linear infinite; }
</style>

