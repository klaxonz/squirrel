<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { computed, ref, watch } from 'vue'
import InputText from 'primevue/inputtext'

defineOptions({ inheritAttrs: false })

const props = defineProps<{
  defaultValue?: string | number
  modelValue?: string | number
  class?: HTMLAttributes['class']
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: string | number): void
}>()

const input = ref<{ $el: HTMLInputElement } | null>(null)

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

defineExpose({
  focus: () => input.value?.$el?.focus(),
  select: () => input.value?.$el?.select(),
})
</script>

<template>
  <InputText
    ref="input"
    v-model="value"
    v-bind="$attrs"
    :class="props.class"
    fluid
  />
</template>
