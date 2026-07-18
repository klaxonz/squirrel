<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <header :class="['sq-dialog__header', $props.class]">
    <slot />
  </header>
</template>
