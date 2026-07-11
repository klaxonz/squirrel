<template>
  <span class="site-tag">
    {{ site }}
  </span>
</template>

<script setup lang="ts">
defineProps<{
  site?: string | null
}>()
</script>

<style scoped>
/* Quiet meta label — system tokens only (media-craft / Spec 2). */
.site-tag {
  display: inline-flex;
  align-items: center;
  max-width: 6rem;
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 500;
  line-height: 1.2;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
