<template>
  <input
    :id="inputId"
    :type="type"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    :min="min"
    :max="max"
    :step="step"
    :class="[
      'input w-full bg-bg-secondary border text-text-primary placeholder-text-muted transition-colors duration-150 focus:outline-none focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed',
      sizeClasses,
      error ? 'border-color-error ring-1 ring-color-error focus:border-color-error focus:ring-color-error' : 'border-border-primary focus:border-color-info focus:ring-color-info'
    ]"
    @input="onInput"
    @blur="onBlur"
    @focus="onFocus"
  >
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: ''
  },
  type: {
    type: String,
    default: 'text',
    validator: (value) => ['text', 'password', 'email', 'number', 'tel', 'url', 'search'].includes(value)
  },
  placeholder: {
    type: String,
    default: ''
  },
  disabled: {
    type: Boolean,
    default: false
  },
  readonly: {
    type: Boolean,
    default: false
  },
  error: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'md',
    validator: (value) => ['sm', 'md', 'lg'].includes(value)
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

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return 'px-2.5 py-1.5 text-xs rounded-md'
    case 'lg':
      return 'px-4 py-3 text-base rounded-lg'
    default:
      return 'px-3 py-2 text-sm rounded-md'
  }
})

const onInput = (event) => {
  const rawValue = event.target.value
  const value = props.type === 'number'
    ? (rawValue === '' ? '' : Number(rawValue))
    : rawValue
  emit('update:modelValue', value)
}

const onBlur = (event) => {
  emit('blur', event)
}

const onFocus = (event) => {
  emit('focus', event)
}
</script>
