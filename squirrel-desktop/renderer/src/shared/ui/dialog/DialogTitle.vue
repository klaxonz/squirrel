<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DialogTitle } from 'reka-ui'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <DialogTitle as="h2" :class="['sq-dialog__title', $props.class]">
    <slot />
  </DialogTitle>
</template>
