<template>
  <AppContentRow
    :class="cn('app-media-item', props.class)"
    :aria-label="ariaLabel"
    :aria-labelledby="ariaLabelledby"
    :disabled="disabled"
    :selected="selected"
    :selectable="selectable"
    @activate="emit('activate', $event)"
  >
    <div v-if="$slots.media" class="app-media-item__media">
      <slot name="media" />
    </div>
    <div class="app-media-item__body">
      <slot />
      <div v-if="$slots.meta" class="app-media-item__meta">
        <slot name="meta" />
      </div>
    </div>

    <template v-if="$slots.actions" #actions>
      <slot name="actions" />
    </template>
  </AppContentRow>
</template>

<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import AppContentRow from './AppContentRow.vue'
import { cn } from '@/shared/lib/utils'

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
  media?: () => unknown
  meta?: () => unknown
  actions?: () => unknown
}>()
</script>

<style scoped>
.app-media-item :deep(.app-content-row__content) {
  align-items: center;
  gap: 0.75rem;
}

.app-media-item__media {
  min-width: 0;
  flex: 0 0 auto;
}

.app-media-item__body {
  min-width: 0;
  flex: 1 1 auto;
}

.app-media-item__meta {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}
</style>
