<template>
  <div class="select-wrapper relative">
    <select
      :id="selectId"
      :value="modelValue"
      :disabled="disabled"
      :class="[
        'select w-full bg-bg-secondary border text-text-primary transition-colors duration-150 focus:outline-none focus:ring-1 disabled:opacity-50 disabled:cursor-not-allowed appearance-none cursor-pointer',
        sizeClasses,
        error ? 'border-color-error ring-1 ring-color-error focus:border-color-error focus:ring-color-error' : 'border-border-primary focus:border-color-info focus:ring-color-info'
      ]"
      @change="onChange"
    >
      <option
        v-if="placeholder"
        value=""
        disabled
        :selected="modelValue === ''"
      >
        {{ placeholder }}
      </option>
      <option
        v-for="option in normalizedOptions"
        :key="option.value"
        :value="option.value"
        :disabled="option.disabled"
      >
        {{ option.label }}
      </option>
    </select>
    <span
      :class="[
        'absolute right-3 pointer-events-none text-text-muted transition-transform duration-150',
        sizeClasses.icon
      ]"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number, Boolean],
    default: ''
  },
  options: {
    type: Array,
    required: true,
    validator: (options) => {
      return options.every(opt => {
        if (typeof opt === 'string' || typeof opt === 'number') return true
        return opt && typeof opt.value !== 'undefined' && typeof opt.label !== 'undefined'
      })
    }
  },
  placeholder: {
    type: String,
    default: ''
  },
  disabled: {
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
  selectId: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:modelValue'])

const normalizedOptions = computed(() => {
  return props.options.map(opt => {
    if (typeof opt === 'string' || typeof opt === 'number') {
      return { value: opt, label: String(opt) }
    }
    return opt
  })
})

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'sm':
      return { select: 'px-2.5 py-1.5 pr-8 text-xs rounded-md', icon: 'top-1.5' }
    case 'lg':
      return { select: 'px-4 py-3 pr-10 text-base rounded-lg', icon: 'top-3.5' }
    default:
      return { select: 'px-3 py-2 pr-9 text-sm rounded-md', icon: 'top-2.5' }
  }
})

const onChange = (event) => {
  const value = props.options.find(opt => {
    if (typeof opt === 'string' || typeof opt === 'number') return String(opt) === event.target.value
    return String(opt.value) === event.target.value
  })
  const emitValue = value ? (typeof value === 'object' ? value.value : value) : event.target.value
  emit('update:modelValue', emitValue)
}
</script>
