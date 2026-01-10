<template>
  <textarea
    :id="textareaId"
    :value="modelValue"
    :placeholder="placeholder"
    :disabled="disabled"
    :readonly="readonly"
    :rows="rows"
    :class="[
      'textarea w-full bg-bg-secondary border text-text-primary placeholder-text-muted transition-colors duration-150 focus:outline-none focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed resize-none',
      sizeClasses,
      error ? 'border-color-error ring-1 ring-color-error focus:border-color-error focus:ring-color-error' : 'border-border-primary focus:border-color-info focus:ring-color-info',
      autoResize && 'overflow-hidden'
    ]"
    @input="onInput"
    @blur="onBlur"
    @focus="onFocus"
    ref="textareaRef"
  />
</template>

<script setup>
import { computed, ref, watch, nextTick } from 'vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
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
  rows: {
    type: Number,
    default: 3
  },
  autoResize: {
    type: Boolean,
    default: false
  },
  textareaId: {
    type: String,
    default: ''
  },
  maxHeight: {
    type: [Number, String],
    default: null
  }
})

const emit = defineEmits(['update:modelValue', 'blur', 'focus'])

const textareaRef = ref(null)

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

const autoResizeTextarea = () => {
  if (!props.autoResize || !textareaRef.value) return

  textareaRef.value.style.height = 'auto'
  const newHeight = textareaRef.value.scrollHeight
  const maxHeightNum = typeof props.maxHeight === 'number'
    ? props.maxHeight
    : props.maxHeight ? parseInt(props.maxHeight) : null

  if (maxHeightNum && newHeight > maxHeightNum) {
    textareaRef.value.style.height = `${maxHeightNum}px`
    textareaRef.value.style.overflowY = 'auto'
  } else {
    textareaRef.value.style.height = `${newHeight}px`
    textareaRef.value.style.overflowY = 'hidden'
  }
}

watch(() => props.modelValue, () => {
  nextTick(autoResizeTextarea)
})

const onInput = (event) => {
  emit('update:modelValue', event.target.value)
  autoResizeTextarea()
}

const onBlur = (event) => {
  emit('blur', event)
}

const onFocus = (event) => {
  emit('focus', event)
}
</script>
