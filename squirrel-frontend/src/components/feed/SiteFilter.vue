<template>
  <Select :model-value="selectedValue" @update:model-value="handleValueChange">
    <SelectTrigger class="toolbar-select">
      <div class="toolbar-select__copy">
        <Bars4Icon class="h-4 w-4 shrink-0 text-muted-foreground" />
        <span v-if="!isMobile" class="toolbar-select__label">站点</span>
        <span class="toolbar-select__value">{{ currentLabel }}</span>
      </div>
    </SelectTrigger>
    <SelectContent class="toolbar-select__content">
      <SelectItem v-for="option in options" :key="option.value" :value="option.value">
        {{ option.label }}
      </SelectItem>
    </SelectContent>
  </Select>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Bars4Icon } from '@heroicons/vue/24/outline'
import { isMobile } from '@/composables/useMobile'
import { useSites } from '@/composables/useSites'
import { Select, SelectContent, SelectItem, SelectTrigger } from '@/components/ui/select'

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

<style scoped>
.toolbar-select {
  width: auto;
  flex: 0 0 auto;
  max-width: 100%;
  min-width: 7rem;
  border-color: hsl(var(--border) / 0.72);
  background: hsl(var(--background));
  box-shadow: none;
}

.toolbar-select__copy {
  display: inline-flex;
  width: 100%;
  align-items: center;
  gap: 0.4rem;
  min-width: 0;
}

.toolbar-select__label {
  font-size: var(--font-size-2xs);
  color: hsl(var(--muted-foreground));
}

.toolbar-select__value {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.toolbar-select__content {
  border-radius: calc(var(--radius-lg) + 2px);
}

@media (max-width: 768px) {
  .toolbar-select {
    min-width: auto;
    width: 2.5rem;
    padding-left: 0.55rem;
    padding-right: 0.55rem;
  }

  .toolbar-select__copy {
    justify-content: center;
  }

  .toolbar-select__value {
    display: none;
  }
}
</style>
