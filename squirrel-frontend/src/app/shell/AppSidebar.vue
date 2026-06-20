<template>
  <!-- Width is owned by the single source of truth: `--sidebar-width` (set on
       AppLayout's wrapper AND on <Sidebar>'s <aside>). Do NOT re-declare a
       conflicting width here — a previous `w-64` (256px) fought the token
       (224/240px) and the outer wrapper, causing inconsistent rail widths. -->
  <Sidebar class="h-full border-r border-border/40 bg-sidebar" />
</template>

<script setup lang="ts">
import Sidebar from '@/shared/components/layout/Sidebar.vue'
</script>
