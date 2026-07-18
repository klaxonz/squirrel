<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import PrimeCard from 'primevue/card'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>

<template>
  <PrimeCard :class="['app-prime-card', $props.class]">
    <template #content><slot /></template>
  </PrimeCard>
</template>
