<template>
  <article
    v-for="i in count"
    :key="i"
    class="w-[18rem] shrink-0 snap-start animate-pulse"
    :style="{ animationDelay: `${i * 60}ms` }"
  >
    <div
      class="relative aspect-video overflow-hidden bg-muted"
      :style="{ borderRadius: 'var(--app-card-radius)' }"
    >
      <div class="absolute inset-0 -translate-x-full animate-[shimmer_1.5s_infinite] bg-gradient-to-r from-transparent via-foreground/5 to-transparent" />
    </div>
    <div class="mt-2 space-y-2">
      <div class="h-4 w-full rounded-md bg-muted" />
      <div class="h-4 w-2/3 rounded-md bg-muted" />
    </div>
    <div class="mt-2 flex items-center gap-1.5">
      <div class="size-4 shrink-0 rounded-full bg-muted" />
      <div class="h-3 w-20 rounded-md bg-muted" />
    </div>
  </article>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  count?: number
}>(), {
  count: 4,
})
</script>

<style scoped>
@keyframes shimmer {
  100% { transform: translateX(100%); }
}
</style>
