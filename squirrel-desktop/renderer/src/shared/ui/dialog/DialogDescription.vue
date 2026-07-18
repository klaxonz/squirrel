<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <p :class="['app-prime-dialog__description', $props.class]">
    <slot />
  </p>
</template>
