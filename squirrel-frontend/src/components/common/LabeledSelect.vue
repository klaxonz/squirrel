<template>
  <div class="labeled-select">
    <label
      v-if="label"
      :for="selectId"
      :class="['block mb-1.5', labelClasses]"
    >
      {{ label }}
      <span v-if="required" class="text-color-error ml-1">*</span>
    </label>
    <Select
      :id="selectId"
      :model-value="modelValue"
      :options="options"
      :placeholder="placeholder"
      :disabled="disabled"
      :error="error"
      :size="size"
      @update:model-value="$emit('update:modelValue', $event)"
    />
    <p v-if="hint && !error" class="mt-1 text-xs text-text-muted">{{ hint }}</p>
    <p v-if="errorText" class="mt-1 text-xs text-color-error">{{ errorText }}</p>
  </div>
</template>

<script setup>
import Select from './Select.vue'
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean],
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  options: {
    type: Array,
    required: true
  },
  placeholder: {
    type: String,
    default: ''
  },
  hint: {
    type: String,
    default: ''
  },
  errorText: {
    type: String,
    default: ''
  },
  error: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  required: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'md'
  },
  labelSize: {
    type: String,
    default: 'sm',
    validator: (value) => ['xs', 'sm', 'md'].includes(value)
  },
  selectId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const labelClasses = computed(() => {
  switch (props.labelSize) {
    case 'xs':
      return 'text-2xs text-text-secondary'
    case 'md':
      return 'text-sm text-text-secondary'
    default:
      return 'text-xs text-text-secondary'
  }
})
</script>
