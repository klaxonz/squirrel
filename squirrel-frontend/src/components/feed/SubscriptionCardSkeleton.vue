<template>
  <div class="p-4 rounded-3xl bg-card border border-border/50 shadow-sm space-y-4">
    <div class="flex items-start gap-4">
      <div class="w-20 h-20 rounded-2xl bg-accent/20 animate-pulse" />
      <div class="flex-1 space-y-3 py-1">
        <div class="h-5 w-2/3 bg-accent/20 rounded-lg animate-pulse" />
        <div class="flex gap-3">
          <div class="h-3 w-16 bg-accent/10 rounded-md animate-pulse" />
          <div class="h-3 w-20 bg-accent/10 rounded-md animate-pulse" />
        </div>
      </div>
    </div>
    <div class="grid grid-cols-3 gap-1.5 pt-2">
      <div v-for="i in 3" :key="i" class="aspect-video rounded-lg bg-accent/10 animate-pulse" />
    </div>
  </div>
</template>
