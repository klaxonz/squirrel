<template>
  <section class="flex flex-col gap-3 border-b border-border pb-3">
    <div class="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
      <div class="min-w-0">
        <div class="flex flex-wrap items-center gap-3">
          <h1 class="text-lg font-semibold tracking-tight text-foreground">同步中心</h1>
          <Badge variant="secondary" class="rounded-full px-2.5 py-1 text-2xs font-medium">
            {{ summary }}
          </Badge>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <Tabs :model-value="lens" class="w-auto" @update:model-value="handleLensUpdate">
          <TabsList class="h-auto rounded-full border border-border bg-card p-1">
            <TabsTrigger value="now" class="rounded-full px-3 py-1.5 text-xs">现在</TabsTrigger>
            <TabsTrigger value="24h" class="rounded-full px-3 py-1.5 text-xs">24h</TabsTrigger>
            <TabsTrigger value="7d" class="rounded-full px-3 py-1.5 text-xs">7d</TabsTrigger>
          </TabsList>
        </Tabs>

        <label class="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground">
          <Switch :checked="autoRefresh" @update:checked="handleAutoRefreshUpdate" />
          <span>自动刷新</span>
        </label>

        <Button variant="secondary" size="sm" class="rounded-full" :disabled="refreshing" @click="emit('refresh')">
          <Loader2 v-if="refreshing" class="h-4 w-4 animate-spin" />
          刷新
        </Button>

        <Button :disabled="!canRetryFailed || retryingBatch" size="sm" class="rounded-full" @click="emit('retry-failed')">
          <Loader2 v-if="retryingBatch" class="h-4 w-4 animate-spin" />
          重试失败项
        </Button>

        <Button variant="ghost" size="sm" class="rounded-full" :disabled="reconciling" @click="emit('reconcile')">
          <Loader2 v-if="reconciling" class="h-4 w-4 animate-spin" />
          对账
        </Button>

        <Badge variant="outline" class="rounded-full px-3 py-1.5 text-2xs font-medium text-muted-foreground">
          更新 {{ lastUpdatedAt || '—' }}
        </Badge>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { SyncTimeLens } from '@/composables/useSyncCenterWorkbench'
import { Loader2 } from 'lucide-vue-next'
import { Badge } from '@/components/ui/badge'
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
