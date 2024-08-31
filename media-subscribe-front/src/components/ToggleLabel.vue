<template>
    <button
      @click="toggle"
      :class="[
        'px-2 py-0.5 rounded-lg text-xs font-medium transition-colors duration-200 ease-in-out',
        modelValue ? 'bg-blue-500 text-white' : 'bg-gray-200 text-gray-700',
        enabled ? 'cursor-pointer hover:bg-opacity-80' : 'opacity-50 cursor-not-allowed'
      ]"
      :disabled="!enabled"
    >
      {{ label }}
    </button>
  </template>
  
  <script>
  export default {
    props: {
      modelValue: Boolean,
      label: String,
      enabled: {
        type: Boolean,
        default: true
      }
    },
    emits: ['update:modelValue'],
    methods: {
      toggle() {
        if (this.enabled) {
          this.$emit('update:modelValue', !this.modelValue);
        }
      }
    }
  }
  </script>