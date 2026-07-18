<script setup lang="ts">
import { computed, provide } from 'vue'
import { dialogContextKey } from './context'

const props = defineProps<{
  open?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:open', value: boolean): void
}>()

const open = computed({
  get: () => props.open ?? false,
  set: (value: boolean) => {
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
