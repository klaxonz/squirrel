<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed } from 'vue'
import { cn } from '@/shared/lib/utils'

type SelectOption = string | number | Record<string, unknown>

defineOptions({ inheritAttrs: false })

const props = withDefaults(defineProps<{
  modelValue?: unknown
  options?: SelectOption[]
  optionLabel?: string
  optionValue?: string
  placeholder?: string
  class?: HTMLAttributes['class']
  size?: 'small' | 'large'
  disabled?: boolean
}>(), {
  options: () => [],
  optionLabel: 'label',
  optionValue: 'value',
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  change: [event: Event]
}>()

const normalizedOptions = computed(() => props.options.map((option) => {
  if (typeof option === 'string' || typeof option === 'number') {
    return { label: String(option), value: String(option), disabled: false }
  }
  return {
    label: String(option[props.optionLabel] ?? option[props.optionValue] ?? ''),
    value: String(option[props.optionValue] ?? option[props.optionLabel] ?? ''),
    disabled: Boolean(option.disabled),
  }
}))

function updateValue(event: Event) {
  emit('update:modelValue', (event.target as HTMLSelectElement).value)
  emit('change', event)
}
</script>

<template>
  <span :class="cn('sq-select', props.size === 'small' && 'sq-select--sm', props.class)">
    <select
      v-bind="$attrs"
      class="sq-select__control"
      :value="String(props.modelValue ?? '')"
      :disabled="props.disabled"
      @change="updateValue"
    >
      <option v-if="props.placeholder" value="" disabled>{{ props.placeholder }}</option>
      <option
        v-for="option in normalizedOptions"
        :key="option.value"
        :value="option.value"
        :disabled="option.disabled"
      >
        {{ option.label }}
      </option>
    </select>
    <svg class="sq-select__chevron" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="m4 6 4 4 4-4" />
    </svg>
  </span>
</template>
