<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <footer :class="['app-prime-dialog__footer', $props.class]">
    <slot />
  </footer>
</template>
