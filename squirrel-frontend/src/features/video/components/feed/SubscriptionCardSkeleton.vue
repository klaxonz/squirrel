<template>
  <div class="space-y-3 rounded-lg border border-border/50 bg-background p-3">
    <div class="flex items-start gap-3">
      <div class="h-11 w-11 animate-pulse rounded-md bg-muted" />
      <div class="flex-1 space-y-2 py-0.5">
        <div class="h-4 w-2/3 animate-pulse rounded-md bg-muted" />
        <div class="flex gap-2">
          <div class="h-3 w-14 animate-pulse rounded bg-muted/70" />
          <div class="h-3 w-16 animate-pulse rounded bg-muted/70" />
        </div>
      </div>
    </div>
    <div class="grid grid-cols-3 gap-1.5">
      <div v-for="i in 3" :key="i" class="aspect-video animate-pulse rounded-md bg-muted/70" />
    </div>
    <div class="border-t border-border/50 pt-2">
      <div class="h-3 w-20 animate-pulse rounded bg-muted/70" />
    </div>
  </div>
</template>
