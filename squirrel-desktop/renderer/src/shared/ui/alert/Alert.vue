<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import Message from 'primevue/message'
import type { AlertVariant } from '.'

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  class?: HTMLAttributes['class']
  variant?: AlertVariant
}>(), {
  variant: 'default',
})

const severity = computed(() => {
  if (props.variant === 'destructive' || props.variant === 'error') return 'error'
  if (props.variant === 'success') return 'success'
  if (props.variant === 'warning') return 'warn'
  if (props.variant === 'info') return 'info'
  return 'secondary'
})
</script>

<template>
  <Message
    v-bind="$attrs"
    :severity="severity"
    :closable="false"
    :class="['app-prime-message', props.class]"
  >
    <slot />
  </Message>
</template>
