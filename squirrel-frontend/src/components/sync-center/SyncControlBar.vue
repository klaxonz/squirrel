<template>
  <section class="flex flex-col gap-4 border-b border-border/60 pb-6">
    <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
      <div class="min-w-0">
        <h1 class="text-xl font-bold tracking-tight text-foreground/90">Dashboard</h1>
        <p class="text-xs font-medium text-muted-foreground/60">{{ summary }}</p>
      </div>

      <div class="flex flex-wrap items-center gap-1.5 rounded-xl border border-border/40 bg-muted/20 p-1">
        <Tabs :model-value="lens" class="w-auto" @update:model-value="handleLensUpdate">
          <TabsList class="h-8 border-none bg-transparent p-0">
            <TabsTrigger value="now" class="h-7 rounded-lg px-4 text-[11px] font-semibold data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm">Now</TabsTrigger>
            <TabsTrigger value="24h" class="h-7 rounded-lg px-4 text-[11px] font-semibold data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm">24H</TabsTrigger>
            <TabsTrigger value="7d" class="h-7 rounded-lg px-4 text-[11px] font-semibold data-[state=active]:bg-background data-[state=active]:text-foreground data-[state=active]:shadow-sm">7D</TabsTrigger>
          </TabsList>
        </Tabs>

        <div class="mx-1 h-4 w-px bg-border/40"></div>

        <Button variant="ghost" size="sm" class="h-8 w-8 p-0 text-muted-foreground/60 hover:text-foreground" :disabled="refreshing" @click="emit('refresh')">
          <Loader2 v-if="refreshing" class="h-4 w-4 animate-spin" />
          <RefreshCcw v-else class="h-4 w-4" />
        </Button>

        <Button variant="ghost" size="sm" class="h-8 text-[11px] font-semibold text-muted-foreground/80 hover:bg-rose-500/10 hover:text-rose-600" :disabled="!canRetryFailed || retryingBatch" @click="emit('retry-failed')">
          <RotateCcw v-if="!retryingBatch" class="mr-2 h-3.5 w-3.5" />
          <Loader2 v-else class="mr-2 h-3.5 w-3.5 animate-spin" />
          Retry Failures
        </Button>

        <Button variant="ghost" size="sm" class="h-8 text-[11px] font-semibold text-muted-foreground/80 hover:text-foreground" :disabled="reconciling" @click="emit('reconcile')">
          <Scale v-if="!reconciling" class="mr-2 h-3.5 w-3.5" />
          <Loader2 v-else class="mr-2 h-3.5 w-3.5 animate-spin" />
          Reconcile
        </Button>

        <div class="mx-1 h-4 w-px bg-border/40"></div>

        <div class="flex items-center gap-2 px-2">
          <Switch :checked="autoRefresh" @update:checked="handleAutoRefreshUpdate" />
          <span class="text-[10px] font-bold uppercase tracking-widest text-muted-foreground/40">Live</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SyncTimeLens } from '@/composables/useSyncCenterWorkbench'
import { Loader2, RefreshCcw, RotateCcw, Scale } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'

const props = defineProps<{
  summary: string
  lens: SyncTimeLens
  autoRefresh: boolean
  canRetryFailed: boolean
  refreshing: boolean
  retryingBatch: boolean
  reconciling: boolean
  lastUpdatedAt: string
}>()

const emit = defineEmits<{
  (e: 'refresh'): void
  (e: 'reconcile'): void
  (e: 'retry-failed'): void
  (e: 'set-lens', value: SyncTimeLens): void
  (e: 'toggle-auto-refresh', value: boolean): void
}>()

const handleLensUpdate = (value: string | number) => {
  emit('set-lens', String(value) as SyncTimeLens)
}

const handleAutoRefreshUpdate = (value: boolean) => {
  emit('toggle-auto-refresh', !!value)
}
</script>