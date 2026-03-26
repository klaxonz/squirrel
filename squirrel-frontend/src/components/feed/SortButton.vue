<template>
  <ToolbarSelect
    :model-value="modelValue"
    :open="open"
    label="排序"
    :current-label="currentLabel"
    :options="sortOptions"
    :icon="Bars4Icon"
    min-width="6.75rem"
    @update:model-value="handleValueChange"
    @update:open="(value) => emit('update:open', value)"
  />
</template>

<script setup>
import { computed } from 'vue'
import { Bars4Icon } from '@heroicons/vue/24/outline'
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

const sortOptions = [
  { value: 'publish_date', label: '上传时间' },
  { value: 'created_at', label: '添加时间' },
]

const currentLabel = computed(() => {
  return sortOptions.find((option) => option.value === props.modelValue)?.label || sortOptions[0].label
})

const handleValueChange = (value) => {
  emit('update:modelValue', String(value))
}
</script>
