<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>
<template><h2 :class="['app-prime-card__title', $props.class]"><slot /></h2></template>
