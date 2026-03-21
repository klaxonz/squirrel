<template>
  <section class="grid grid-cols-1 gap-3 2xl:grid-cols-[1.25fr_1fr]">
    <div class="rounded-2xl border border-border-primary bg-bg-secondary">
      <div class="flex items-center justify-between border-b border-border-primary px-3 py-2.5">
        <h2 class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">当前态势</h2>
        <span class="text-2xs text-text-muted">{{ current.length }} 项</span>
      </div>
      <div class="grid grid-cols-2 gap-px bg-border-primary lg:grid-cols-3">
        <button
          v-for="item in current"
          :key="item.key"
          type="button"
          class="min-h-[4.75rem] bg-bg-primary px-3 py-2.5 text-left transition-colors hover:bg-bg-hover"
          @click="emit('select', item.key)"
        >
          <div class="text-2xs text-text-tertiary">{{ item.label }}</div>
          <div class="mt-1.5 flex items-center justify-between gap-3">
            <span class="text-base font-semibold" :class="getValueClass(item.tone)">{{ item.value }}</span>
            <span class="h-2 w-2 rounded-full" :class="getDotClass(item.tone)"></span>
          </div>
          <div v-if="item.delta" class="mt-1 text-2xs text-text-muted">{{ item.delta }}</div>
        </button>
      </div>
    </div>

    <div class="rounded-2xl border border-border-primary bg-bg-secondary">
      <div class="flex items-center justify-between border-b border-border-primary px-3 py-2.5">
        <h2 class="text-xs font-semibold tracking-[0.14em] text-text-tertiary">最近变化</h2>
        <span class="text-2xs text-text-muted">{{ recent.length }} 项</span>
      </div>
      <div class="grid grid-cols-2 gap-px bg-border-primary lg:grid-cols-3">
        <button
          v-for="item in recent"
          :key="item.key"
          type="button"
          class="min-h-[4.75rem] bg-bg-primary px-3 py-2.5 text-left transition-colors hover:bg-bg-hover"
          @click="emit('select', item.key)"
        >
          <div class="text-2xs text-text-tertiary">{{ item.label }}</div>
          <div class="mt-1.5 flex items-center justify-between gap-3">
            <span class="text-base font-semibold" :class="getValueClass(item.tone)">{{ item.value }}</span>
            <span class="h-2 w-2 rounded-full" :class="getDotClass(item.tone)"></span>
          </div>
          <div v-if="item.delta" class="mt-1 text-2xs text-text-muted">{{ item.delta }}</div>
        </button>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
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
      return 'text-color-error'
    case 'info':
      return 'text-color-info'
    case 'warning':
      return 'text-color-warning'
    case 'success':
      return 'text-color-success'
    default:
      return 'text-text-primary'
  }
}

const getDotClass = (tone: SignalTone) => {
  switch (tone) {
    case 'error':
      return 'bg-color-error'
    case 'info':
      return 'bg-color-info'
    case 'warning':
      return 'bg-color-warning'
    case 'success':
      return 'bg-color-success'
    default:
      return 'bg-text-muted'
  }
}
</script>
