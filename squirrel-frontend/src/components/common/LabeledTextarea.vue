<template>
  <div class="labeled-textarea">
    <label
      v-if="label"
      :for="textareaId"
      :class="['block mb-1.5', labelClasses]"
    >
      {{ label }}
      <span v-if="required" class="text-color-error ml-1">*</span>
    </label>
    <Textarea
      :id="textareaId"
      :model-value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :error="error"
      :size="size"
      :rows="rows"
      :auto-resize="autoResize"
      @update:model-value="$emit('update:modelValue', $event)"
      @blur="$emit('blur', $event)"
      @focus="$emit('focus', $event)"
    />
    <p v-if="hint && !error" class="mt-1 text-xs text-text-muted">{{ hint }}</p>
    <p v-if="errorText" class="mt-1 text-xs text-color-error">{{ errorText }}</p>
  </div>
</template>

<script setup>
import Textarea from './Textarea.vue'
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  label: {
    type: String,
    default: ''
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
  rows: {
    type: Number,
    default: 3
  },
  autoResize: {
    type: Boolean,
    default: false
  },
  labelSize: {
    type: String,
    default: 'sm',
    validator: (value) => ['xs', 'sm', 'md'].includes(value)
  },
  textareaId: {
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
</script>
