<template>
  <div>
    <label class="block text-xs text-text-muted mb-1">{{ label }}</label>
    <input
      type="number"
      :step="step"
      :min="min"
      :max="max"
      v-model="internalValue"
      class="w-full bg-bg-tertiary border border-border-secondary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error"
      :placeholder="placeholder"
    >
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: { type: String, required: true },
  modelValue: { type: [Number, String], default: '' },
  step: { type: [Number, String], default: 1 },
  min: { type: [Number, String], default: undefined },
  max: { type: [Number, String], default: undefined },
  placeholder: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue']);

const internalValue = computed({
  get() {
    return props.modelValue;
  },
  set(val) {
    emit('update:modelValue', val === '' ? '' : Number(val));
  },
});
</script>
