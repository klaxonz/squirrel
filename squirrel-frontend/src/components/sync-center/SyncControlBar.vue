<template>
  <section class="flex flex-col gap-2 border-b border-white/10 pb-4 mb-4">
    <div class="flex items-baseline gap-4">
      <h1 class="text-2xl font-black tracking-[0.15em] text-white/90 uppercase font-mono">
        信号监控
      </h1>
      <div class="h-1 w-1 rounded-full bg-orange-500 glow-amber"></div>
    </div>
    <p class="text-[10px] font-bold text-white/30 uppercase tracking-[0.3em] font-mono">
      {{ summary }}
    </p>
  </section>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  summary: string
}>(), {})
</script>
