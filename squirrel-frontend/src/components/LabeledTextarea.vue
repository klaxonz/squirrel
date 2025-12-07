<template>
  <div>
    <label class="block text-xs text-gray-400 mb-1">{{ label }}</label>
    <textarea
      v-model="internalValue"
      :rows="rows"
      class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-red-500"
      :placeholder="placeholder"
    ></textarea>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  label: { type: String, required: true },
  modelValue: { type: String, default: '' },
  rows: { type: Number, default: 3 },
  placeholder: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue']);

const internalValue = computed({
  get() {
    return props.modelValue;
  },
  set(val) {
    emit('update:modelValue', val);
  },
});
</script>
