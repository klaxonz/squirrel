<template>
  <Button
    variant="outline"
    size="sm"
    :class="['refresh-button', customClass]"
    :title="title"
    :aria-label="ariaLabel || title"
    @click="$emit('click')"
  >
    <ArrowPathIcon :class="['h-4 w-4', { 'spin-anim': isSpinning }]" />
    <span class="sr-only">{{ ariaLabel || title }}</span>
  </Button>
</template>

<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { ArrowPathIcon } from '@heroicons/vue/24/outline'
import { Button } from '@/components/ui/button'

const props = defineProps({
  loading: { type: Boolean, default: false },
  minSpinMs: { type: Number, default: 800 },
  title: { type: String, default: '刷新' },
  ariaLabel: { type: String, default: '' },
  customClass: { type: String, default: '' },
})

defineEmits(['click'])

const isSpinning = ref(false)
let spinStartAt = 0
let timer = null

const clearTimer = () => {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }
}

watch(
  () => props.loading,
  (value) => {
    if (value) {
      clearTimer()
      isSpinning.value = true
      spinStartAt = Date.now()
      return
    }

    const elapsed = Date.now() - spinStartAt
    const remain = Math.max(0, props.minSpinMs - elapsed)
    clearTimer()
    timer = setTimeout(() => {
      isSpinning.value = false
      clearTimer()
    }, remain)
  },
)

onUnmounted(() => {
  clearTimer()
})
</script>

<style scoped>
.refresh-button {
  min-width: 2rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.spin-anim {
  animation: spin 0.8s linear infinite;
}
</style>
