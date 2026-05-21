<template>
  <div :class="[
    layout === 'list' ? 'flex flex-row gap-4' : 'flex flex-col gap-3',
    'animate-pulse'
  ]" :style="{ animationDelay: `${delay}ms` }">
    <div :class="[
      layout === 'list' ? 'w-48 shrink-0 md:w-64 relative aspect-video rounded-xl bg-muted overflow-hidden' : 'relative aspect-video rounded-xl bg-muted overflow-hidden'
    ]">
      <div class="absolute inset-0 bg-gradient-to-r from-transparent via-foreground/5 to-transparent -translate-x-full animate-[shimmer_1.5s_infinite]" />
    </div>
    <div :class="[
      layout === 'list' ? 'flex-1 py-1 flex flex-col justify-center' : 'flex gap-3 px-1'
    ]">
      <div v-if="layout === 'grid'" class="h-9 w-9 shrink-0 rounded-full bg-muted" />
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
  layout?: 'grid' | 'list'
}>()
</script>

<style scoped>
@keyframes shimmer {
  100% { transform: translateX(100%); }
}
</style>
