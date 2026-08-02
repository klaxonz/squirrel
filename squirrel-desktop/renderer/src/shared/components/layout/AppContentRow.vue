<template>
  <div
    :class="cn('app-content-row', selected && 'is-selected', props.class)"
    v-bind="$attrs"
  >
    <button
      class="app-content-row__primary"
      type="button"
      :disabled="disabled"
      :aria-label="ariaLabel || undefined"
      :aria-labelledby="ariaLabel ? undefined : (ariaLabelledby || contentId)"
      :aria-pressed="selectable ? selected : undefined"
      @click="emit('activate', $event)"
    />
    <div :id="contentId" class="app-content-row__content">
      <slot />
    </div>
    <div v-if="$slots.actions" class="app-content-row__actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { useId } from 'vue'
import { cn } from '@/shared/lib/utils'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  ariaLabel?: string
  ariaLabelledby?: string
  disabled?: boolean
  selected?: boolean
  selectable?: boolean
  class?: HTMLAttributes['class']
}>(), {
  ariaLabel: '',
  ariaLabelledby: '',
  disabled: false,
  selected: false,
  selectable: false,
})

const emit = defineEmits<{
  activate: [event: MouseEvent]
}>()

defineSlots<{
  default: () => unknown
  actions?: () => unknown
}>()

const contentId = `app-content-row-${useId()}-content`
</script>

<style scoped>
.app-content-row {
  position: relative;
  display: flex;
  min-width: 0;
}

.app-content-row__primary {
  position: absolute;
  z-index: 0;
  inset: 0;
  width: 100%;
  border: 0;
  padding: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
}

.app-content-row__primary:disabled {
  cursor: default;
}

.app-content-row__primary:focus-visible {
  outline: 2px solid hsl(var(--ring));
  outline-offset: -2px;
}

.app-content-row__content {
  position: relative;
  z-index: 1;
  display: flex;
  min-width: 0;
  flex: 1 1 auto;
  pointer-events: none;
}

.app-content-row__content :deep(a),
.app-content-row__content :deep(button),
.app-content-row__content :deep(input),
.app-content-row__content :deep(select),
.app-content-row__content :deep(textarea),
.app-content-row__content :deep([tabindex]) {
  pointer-events: auto;
}

.app-content-row__actions {
  position: relative;
  z-index: 2;
  display: flex;
  flex: 0 0 auto;
  align-items: center;
}
</style>
