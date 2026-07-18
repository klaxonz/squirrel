<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import { DialogDescription } from 'reka-ui'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <DialogDescription as="p" :class="['sq-dialog__description', $props.class]">
    <slot />
  </DialogDescription>
</template>
