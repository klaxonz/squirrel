<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import PrimeCheckbox from 'primevue/checkbox'

defineOptions({ inheritAttrs: false })

defineProps<{
  modelValue?: boolean
  disabled?: boolean
  class?: HTMLAttributes['class']
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: boolean): void
}>()
</script>

<template>
  <PrimeCheckbox
    v-bind="$attrs"
    :model-value="modelValue"
    :disabled="disabled"
    :class="$props.class"
    binary
    @update:model-value="emit('update:modelValue', Boolean($event))"
  />
</template>
