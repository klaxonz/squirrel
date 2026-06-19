<template>
  <div class="app-skeleton-text">
    <AppSkeleton
      v-for="i in count"
      :key="i"
      :width="widthFor(i)"
      height="0.75rem"
      rounded="0.25rem"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppSkeleton from './AppSkeleton.vue'

/**
 * A vertical stack of placeholder text lines. Pass `widths` for full control,
 * or `lines` + `width` for uniform lines (last line defaults narrower like real
 * text). Builds on AppSkeleton so the base color stays unified.
 */
const props = withDefaults(defineProps<{
  lines?: number
  /** Width for all lines when `widths` is not set. */
  width?: string
  /** Per-line widths (1-based). Takes precedence over `width`. */
  widths?: string[]
}>(), {
  lines: 2,
  width: '100%',
  widths: () => [],
})

const count = computed(() => props.widths.length || props.lines)

function widthFor(index: number): string {
  if (props.widths.length) return props.widths[index - 1] ?? props.width
  // Last line slightly shorter, like wrapped text.
  if (index === count.value && count.value > 1) return '66%'
  return props.width
}
</script>

<style scoped>
.app-skeleton-text {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
</style>
