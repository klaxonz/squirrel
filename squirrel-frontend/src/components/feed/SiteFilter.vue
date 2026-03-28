<template>
  <ToolbarSelect
    :model-value="selectedValue"
    label="站点"
    :current-label="currentLabel"
    :options="options"
    :icon="Bars4Icon"
    min-width="7rem"
    @update:model-value="handleValueChange"
  />
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Bars4Icon } from '@heroicons/vue/24/outline'
import { useSites } from '@/composables/useSites'
import ToolbarSelect from './ToolbarSelect.vue'

const ALL_SITES_VALUE = '__all_sites__'

const props = defineProps({
  modelValue: {
    type: String,
    default: undefined,
  },
})

const emit = defineEmits(['update:modelValue'])

const options = ref([{ value: ALL_SITES_VALUE, label: '全部站点' }])
const { options: cachedOptions, fetchSites } = useSites()

const selectedValue = computed(() => props.modelValue ?? ALL_SITES_VALUE)

const currentLabel = computed(() => {
  const found = options.value.find((option) => option.value === selectedValue.value)
  return found ? found.label : '全部站点'
})

const handleValueChange = (value) => {
  if (value === ALL_SITES_VALUE) {
    emit('update:modelValue', undefined)
    return
  }

  emit('update:modelValue', String(value))
}

const normalizeOptions = (items) => {
  const mappedItems = (items || [])
    .map((option) => ({
      value: option.value ?? ALL_SITES_VALUE,
      label: option.label,
    }))
    .filter((option) => option.value !== ALL_SITES_VALUE)

  return [{ value: ALL_SITES_VALUE, label: '全部站点' }, ...mappedItems]
}

onMounted(async () => {
  if (cachedOptions.value) {
    options.value = normalizeOptions(cachedOptions.value)
    return
  }

  const { data } = await fetchSites()
  if (data) {
    options.value = normalizeOptions(data)
  }
})
</script>
