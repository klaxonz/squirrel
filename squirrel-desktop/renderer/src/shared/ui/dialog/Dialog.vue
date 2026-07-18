<script setup lang="ts">
import { DialogRoot } from 'reka-ui'

defineProps<{ open?: boolean }>()

defineEmits<{
  'update:open': [value: boolean]
}>()
</script>

<template>
  <DialogRoot :open="Boolean(open)" @update:open="$emit('update:open', $event)">
    <slot />
  </DialogRoot>
</template>
