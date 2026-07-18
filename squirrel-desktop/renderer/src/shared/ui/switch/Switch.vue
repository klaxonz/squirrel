<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import ToggleSwitch from 'primevue/toggleswitch'

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
  <ToggleSwitch
    v-bind="$attrs"
    :model-value="modelValue"
    :disabled="disabled"
    :class="$props.class"
    @update:model-value="emit('update:modelValue', Boolean($event))"
  />
</template>
