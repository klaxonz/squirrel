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

        <div class="flex items-center gap-2">
          <button 
            class="tactical-btn" 
            :disabled="refreshing" 
            @click="emit('refresh')"
          >
            [ {{ refreshing ? '刷新中...' : '刷新全部' }} ]
          </button>

          <button 
            class="tactical-btn" 
            :disabled="!canRetryFailed || retryingBatch" 
            @click="emit('retry-failed')"
          >
            [ {{ retryingBatch ? '重试中...' : '重试失败项' }} ]
          </button>

          <button 
            class="tactical-btn" 
            :disabled="!canReconcile || reconciling" 
            @click="emit('reconcile')"
          >
            [ {{ reconciling ? '协调中...' : '状态协调' }} ]
          </button>
        </div>

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
  canRetryFailed: boolean
  canReconcile?: boolean
  refreshing: boolean
  retryingBatch: boolean
  reconciling: boolean
  lastUpdatedAt: string
}>(), {
  canReconcile: true,
})

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'reconcile'): void
  (e: 'retry-failed'): void
  (e: 'set-lens', value: SyncTimeLens): void
}>()

const handleLensUpdate = (value: string | number) => {
  emit('set-lens', String(value) as SyncTimeLens)
}
</script>

<style scoped>
.tactical-btn {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.4);
  padding: 0.5rem 0.75rem;
  transition: all 0.2s ease;
  letter-spacing: 0.1em;
}

.tactical-btn:hover:not(:disabled) {
  color: #ff4d00;
  text-shadow: 0 0 10px rgba(255, 77, 0, 0.5);
}

.tactical-btn:disabled {
  opacity: 0.2;
  cursor: not-allowed;
}
</style>
