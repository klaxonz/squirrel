<template>
  <section class="grid grid-cols-1 gap-3 2xl:grid-cols-[1.25fr_1fr]">
    <Card class="rounded-lg">
      <CardHeader class="flex flex-row items-center justify-between space-y-0 px-4 py-3">
        <div class="space-y-0.5">
          <CardTitle class="text-sm">当前态势</CardTitle>
          <CardDescription class="text-2xs">点击任意指标快速过滤</CardDescription>
        </div>
        <Badge variant="secondary" class="rounded-md px-2 py-0.5 text-2xs font-normal text-muted-foreground/80">
          {{ current.length }} 项
        </Badge>
      </CardHeader>
      <CardContent class="px-4 pb-4 pt-0">
        <div class="grid grid-cols-2 gap-2 lg:grid-cols-3">
          <button
            v-for="item in current"
            :key="item.key"
            type="button"
            class="group min-h-[4.75rem] rounded-lg border border-border bg-background px-3 py-2.5 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            @click="emit('select', item.key)"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="text-2xs text-muted-foreground/70">{{ item.label }}</div>
              <span class="h-2 w-2 rounded-full" :class="getDotClass(item.tone)"></span>
            </div>
            <div class="mt-1.5 text-lg font-semibold tabular-nums" :class="getValueClass(item.tone)">
              {{ item.value }}
            </div>
            <div v-if="item.delta" class="mt-1 line-clamp-1 text-2xs text-muted-foreground">
              {{ item.delta }}
            </div>
          </button>
        </div>
      </CardContent>
    </Card>

    <Card class="rounded-lg">
      <CardHeader class="flex flex-row items-center justify-between space-y-0 px-4 py-3">
        <div class="space-y-0.5">
          <CardTitle class="text-sm">最近变化</CardTitle>
          <CardDescription class="text-2xs">聚合最近窗口内的成功率与波动</CardDescription>
        </div>
        <Badge variant="secondary" class="rounded-md px-2 py-0.5 text-2xs font-normal text-muted-foreground/80">
          {{ recent.length }} 项
        </Badge>
      </CardHeader>
      <CardContent class="px-4 pb-4 pt-0">
        <div class="grid grid-cols-2 gap-2 lg:grid-cols-3">
          <button
            v-for="item in recent"
            :key="item.key"
            type="button"
            class="group min-h-[4.75rem] rounded-lg border border-border bg-background px-3 py-2.5 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            @click="emit('select', item.key)"
          >
            <div class="flex items-center justify-between gap-2">
              <div class="text-2xs text-muted-foreground/70">{{ item.label }}</div>
              <span class="h-2 w-2 rounded-full" :class="getDotClass(item.tone)"></span>
            </div>
            <div class="mt-1.5 text-lg font-semibold tabular-nums" :class="getValueClass(item.tone)">
              {{ item.value }}
            </div>
            <div v-if="item.delta" class="mt-1 line-clamp-1 text-2xs text-muted-foreground">
              {{ item.delta }}
            </div>
          </button>
        </div>
      </CardContent>
    </Card>
  </section>
</template>

<script setup lang="ts">
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

type SignalTone = 'neutral' | 'info' | 'warning' | 'error' | 'success'

export interface SyncSignalItem {
  key: string
  label: string
  value: string | number
  tone: SignalTone
  delta?: string
}

defineProps<{
  current: SyncSignalItem[]
  recent: SyncSignalItem[]
}>()

const emit = defineEmits<{
  (e: 'select', key: string): void
}>()

const getValueClass = (tone: SignalTone) => {
  switch (tone) {
    case 'error':
      return 'text-destructive'
    case 'info':
      return 'text-blue-500'
    case 'warning':
      return 'text-amber-500'
    case 'success':
      return 'text-emerald-500'
    default:
      return 'text-foreground'
  }
}

const getDotClass = (tone: SignalTone) => {
  switch (tone) {
    case 'error':
      return 'bg-destructive'
    case 'info':
      return 'bg-blue-500'
    case 'warning':
      return 'bg-amber-500'
    case 'success':
      return 'bg-emerald-500'
    default:
      return 'bg-muted-foreground/40'
  }
}

</script>
