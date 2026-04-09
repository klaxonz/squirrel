<template>
  <ToolbarSelect
    v-if="loaded && settings.showNsfw"
    :model-value="modelValue"
    label="敏感内容"
    :current-label="currentLabel"
    :options="nsfwOptions"
    :icon="ShieldCheckIcon"
    min-width="7.5rem"
    @update:model-value="handleValueChange"
  />
</template>

<script setup>
import { computed, onMounted, watch } from 'vue'
import { ShieldCheckIcon } from '@heroicons/vue/24/outline'
import { useUserSettings } from '@/composables/useUserSettings'
import ToolbarSelect from './ToolbarSelect.vue'

const props = defineProps({
  modelValue: {
    type: String,
    required: true,
  },
})

const emit = defineEmits(['update:modelValue'])
const { settings, loaded, loadUserSettings } = useUserSettings()

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

onMounted(() => {
  loadUserSettings()
})

watch(
  () => [loaded.value, settings.value.showNsfw, props.modelValue],
  ([isLoaded, showNsfw, modelValue]) => {
    if (isLoaded && !showNsfw && modelValue === 'yes') {
      emit('update:modelValue', 'all')
    }
  },
  { immediate: true },
)
</script>
