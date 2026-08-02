<template>
  <Transition name="new-content-bar">
    <button
      v-if="visible"
      type="button"
      class="new-content-bar"
      :aria-label="label"
      @click="$emit('apply')"
    >
      <AppIcon name="chevronDown" class="new-content-bar__icon" aria-hidden="true" />
      <span class="new-content-bar__label">{{ label }}</span>
    </button>
  </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'

const props = withDefaults(defineProps<{
  count?: number
  visible: boolean
}>(), {
  count: 0,
})

defineEmits<{
  apply: []
}>()

const label = computed(() => {
  const count = Number(props.count)
  return count > 0 ? `查看 ${count} 条新内容` : '查看新内容'
})
</script>

<style scoped>
/*
  Reddit-style "view new posts" affordance: a quiet hairline bar that slides
  down over the top of the feed. Purely declarative — visibility, counting and
  apply semantics live in the caller (useNewContentDetector).
*/
.new-content-bar {
  display: flex;
  width: 100%;
  min-height: 2.25rem;
  align-items: center;
  justify-content: center;
  gap: 0.375rem;
  border: 1px solid var(--app-hairline);
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  color: hsl(var(--primary));
  box-shadow: var(--shadow-xs);
  padding-inline: var(--space-4);
  cursor: pointer;
  font-size: var(--app-text-body-size);
  font-weight: 600;
  line-height: 1.2;
  transition:
    background-color var(--duration-fast) var(--ease-default),
    border-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.new-content-bar:hover,
.new-content-bar:focus-visible {
  border-color: hsl(var(--primary) / 0.45);
  background: var(--app-row-hover-bg);
}

.new-content-bar:focus-visible {
  outline: 2px solid hsl(var(--ring) / 0.6);
  outline-offset: 1px;
}

.new-content-bar__icon {
  flex: none;
  width: 0.875rem;
  height: 0.875rem;
}

.new-content-bar__label {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* Subtle fade + slide-down on entry, fade on exit — restrained, Reddit-kosher. */
.new-content-bar-enter-active,
.new-content-bar-leave-active {
  transition:
    opacity var(--duration-base) var(--ease-default),
    transform var(--duration-base) var(--ease-default);
}

.new-content-bar-enter-from {
  opacity: 0;
  transform: translateY(-0.5rem);
}

.new-content-bar-leave-to {
  opacity: 0;
}

@media (prefers-reduced-motion: reduce) {
  .new-content-bar-enter-active,
  .new-content-bar-leave-active {
    transition: none;
  }

  .new-content-bar-enter-from {
    transform: none;
  }
}
</style>
