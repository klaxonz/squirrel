<template>
  <div class="labeled-input">
    <label
      v-if="label"
      :for="inputId"
      :class="['block mb-1.5', labelClasses]"
    >
      {{ label }}
      <span v-if="required" class="text-color-error ml-1">*</span>
    </label>
    <Input
      :id="inputId"
      :model-value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :disabled="disabled"
      :error="error"
      :size="size"
      :min="min"
      :max="max"
      :step="step"
      @update:model-value="$emit('update:modelValue', $event)"
      @blur="$emit('blur', $event)"
      @focus="$emit('focus', $event)"
    />
    <p v-if="hint && !error" class="mt-1 text-xs text-text-muted">{{ hint }}</p>
    <p v-if="errorText" class="mt-1 text-xs text-color-error">{{ errorText }}</p>
  </div>
</template>

<script setup>
import Input from './Input.vue'
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  label: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'text'
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
  inputId: {
    type: String,
    default: ''
  },
  min: {
    type: [Number, String],
    default: undefined
  },
  max: {
    type: [Number, String],
    default: undefined
  },
  step: {
    type: [Number, String],
    default: undefined
  }
})

const emit = defineEmits(['update:modelValue', 'blur', 'focus'])

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
