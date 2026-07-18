<script setup lang="ts">
import { computed, provide, ref } from 'vue'
import { dialogContextKey } from './context'

const props = withDefaults(defineProps<{
  open?: boolean
  defaultOpen?: boolean
}>(), {
  defaultOpen: false,
})

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
}>()

const internalOpen = ref(props.defaultOpen)
const open = computed({
  get: () => props.open ?? internalOpen.value,
  set: (value: boolean) => {
    internalOpen.value = value
    emit('update:open', value)
  },
})

provide(dialogContextKey, {
  open,
  setOpen: (value) => { open.value = value },
})
</script>

<template>
  <slot />
</template>
