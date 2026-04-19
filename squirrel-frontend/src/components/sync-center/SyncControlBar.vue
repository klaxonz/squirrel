<template>
  <section class="flex flex-col gap-1 md:gap-2 border-b border-border/50 pb-4 mb-4">
    <p class="text-[9px] sm:text-[10px] font-bold text-muted-foreground/60 uppercase tracking-[0.1em] sm:tracking-[0.3em] font-mono leading-relaxed">
      {{ summary }}
    </p>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  summary: string
}>(), {})
</script>
