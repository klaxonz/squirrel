<template>
  <label class="flex items-center gap-2 cursor-pointer select-none">
    <input
      type="checkbox"
      v-model="internalValue"
      class="accent-red-500"
    >
    <span>{{ label }}</span>
  </label>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: { type: String, required: true },
  modelValue: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue']);

const internalValue = computed({
  get() {
    return props.modelValue;
  },
  set(val) {
    emit('update:modelValue', !!val);
  },
});
</script>
