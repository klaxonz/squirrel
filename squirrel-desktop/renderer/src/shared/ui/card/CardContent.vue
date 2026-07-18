<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
defineProps<{ class?: HTMLAttributes['class'] }>()
</script>
<template><div :class="['app-prime-card__body', $props.class]"><slot /></div></template>
