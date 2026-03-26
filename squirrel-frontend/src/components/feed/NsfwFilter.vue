<template>
  <ToolbarSelect
    :model-value="modelValue"
    :open="open"
    label="敏感内容"
    :current-label="currentLabel"
    :options="nsfwOptions"
    :icon="ShieldCheckIcon"
    min-width="7.5rem"
    @update:model-value="handleValueChange"
    @update:open="(value) => emit('update:open', value)"
  />
</template>

<script setup>
import { computed } from 'vue'
import { ShieldCheckIcon } from '@heroicons/vue/24/outline'
import ToolbarSelect from './ToolbarSelect.vue'

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
  open: {
    type: Boolean,
    default: false,
  },
})

const emit = defineEmits(['update:modelValue', 'update:open'])

const nsfwOptions = [
  { value: 'all', label: '全部' },
  { value: 'yes', label: '仅 NSFW' },
  { value: 'no', label: '仅安全内容' },
]

const currentLabel = computed(() => {
  return nsfwOptions.find((option) => option.value === props.modelValue)?.label || '全部'
})

const handleValueChange = (value) => {
  emit('update:modelValue', String(value))
}
</script>
