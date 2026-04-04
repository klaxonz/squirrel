<template>
  <section class="flex flex-col gap-4 border-b border-border/10 pb-6">
    <div class="min-w-0">
      <div class="min-w-0">
        <h1 class="text-xl font-bold tracking-tighter text-foreground/90 uppercase font-mono">信号监控</h1>
        <p class="text-[10px] font-medium text-orange-500/60 uppercase tracking-[0.2em] font-mono">{{ summary }}</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  summary: string
}>(), {})
</script>
