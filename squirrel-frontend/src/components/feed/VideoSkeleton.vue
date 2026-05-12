<template>
  <div class="flex flex-col gap-3" :style="{ animationDelay: `${delay}ms` }">
    <div class="relative aspect-video rounded-xl bg-muted overflow-hidden">
      <div class="absolute inset-0 bg-gradient-to-r from-transparent via-foreground/5 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
    </div>
    <div class="flex gap-3 px-1">
      <div class="h-9 w-9 shrink-0 rounded-full bg-muted" />
      <div class="flex-1 space-y-2">
        <div class="h-4 bg-muted rounded-md w-full" />
        <div class="h-3 bg-muted rounded-md w-2/3" />
        <div class="flex gap-2 pt-1">
          <div class="h-3 bg-muted rounded-md w-16" />
          <div class="h-3 bg-muted rounded-md w-12" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  delay?: number
}>()
</script>

<style scoped>
@keyframes shimmer {
  100% { transform: translateX(100%); }
}
</style>
