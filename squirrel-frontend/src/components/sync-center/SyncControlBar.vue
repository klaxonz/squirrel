<template>
  <section class="flex flex-col gap-4 border-b border-border/10 pb-6">
    <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div class="min-w-0">
        <h1 class="text-xl font-bold tracking-tighter text-foreground/90 uppercase font-mono">信号监控</h1>
        <p class="text-[10px] font-medium text-orange-500/60 uppercase tracking-[0.2em] font-mono">{{ summary }}</p>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <Tabs :model-value="lens" class="w-auto" @update:model-value="handleLensUpdate">
          <TabsList class="h-8 border border-white/5 bg-black/40 p-1">
            <TabsTrigger value="now" class="h-6 rounded px-3 text-[10px] font-bold uppercase tracking-wider data-[state=active]:bg-orange-500/20 data-[state=active]:text-orange-500">实时</TabsTrigger>
            <TabsTrigger value="24h" class="h-6 rounded px-3 text-[10px] font-bold uppercase tracking-wider data-[state=active]:bg-orange-500/20 data-[state=active]:text-orange-500">24小时</TabsTrigger>
            <TabsTrigger value="7d" class="h-6 rounded px-3 text-[10px] font-bold uppercase tracking-wider data-[state=active]:bg-orange-500/20 data-[state=active]:text-orange-500">7天</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SyncTimeLens } from '@/composables/useSyncCenterWorkbench'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

withDefaults(defineProps<{
  summary: string
  lens: SyncTimeLens
}>(), {})

const emit = defineEmits<{
  (e: 'set-lens', value: SyncTimeLens): void
}>()

const handleLensUpdate = (value: string | number) => {
  emit('set-lens', String(value) as SyncTimeLens)
}
</script>
