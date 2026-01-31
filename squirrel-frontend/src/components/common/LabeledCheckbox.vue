<template>
  <div class="labeled-checkbox">
    <label
      v-if="label"
      :for="checkboxId"
      :class="['inline-flex items-center gap-2', labelClasses]"
    >
      <input
        :id="checkboxId"
        type="checkbox"
        :checked="modelValue"
        :disabled="disabled"
        :class="[
          'h-4 w-4 rounded border border-border-primary bg-bg-secondary text-color-error focus:outline-none focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed',
          error ? 'border-color-error ring-1 ring-color-error focus:ring-color-error' : 'focus:ring-color-info'
        ]"
        @change="onChange"
        @blur="onBlur"
        @focus="onFocus"
      >
      <span class="select-none">
        {{ label }}
        <span v-if="required" class="text-color-error ml-1">*</span>
      </span>
    </label>
    <p v-if="hint && !error" class="mt-1 text-xs text-text-muted">{{ hint }}</p>
    <p v-if="errorText" class="mt-1 text-xs text-color-error">{{ errorText }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  label: {
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
  labelSize: {
    type: String,
    default: 'sm',
    validator: (value) => ['xs', 'sm', 'md'].includes(value)
  },
  checkboxId: {
    type: String,
    default: ''
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

const onChange = (event) => {
  emit('update:modelValue', event.target.checked)
}

const onBlur = (event) => {
  emit('blur', event)
}

const onFocus = (event) => {
  emit('focus', event)
}
</script>

