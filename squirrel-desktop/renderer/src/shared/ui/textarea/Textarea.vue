<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, ref, watch } from 'vue'
import PrimeTextarea from 'primevue/textarea'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  class?: HTMLAttributes['class']
  defaultValue?: string | number
  modelValue?: string | number
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void
}>()

const internalValue = ref(String(props.defaultValue ?? ''))
watch(() => props.defaultValue, (value) => {
  if (props.modelValue === undefined) internalValue.value = String(value ?? '')
})

const value = computed({
  get: () => String(props.modelValue ?? internalValue.value),
  set: (next: string) => {
    internalValue.value = next
    emit('update:modelValue', next)
  },
})
</script>

<template>
  <PrimeTextarea
    v-model="value"
    v-bind="$attrs"
    :class="props.class"
    fluid
  />
</template>
