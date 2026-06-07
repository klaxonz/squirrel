<template>
  <div class="relative w-full" ref="dropdownRef">
    <button
      @click="$emit('toggle')"
      class="flex h-8 w-full items-center justify-between rounded-lg border border-transparent bg-accent/40 hover:bg-accent/60 px-2.5 text-xs font-semibold transition-all"
      :class="selectedId ? 'text-foreground border-primary/20 bg-primary/5' : 'text-muted-foreground'"
    >
      <div class="flex items-center gap-2 min-w-0">
        <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 text-primary" />
        <span class="truncate">{{ selectedName || '选择账号...' }}</span>
      </div>
      <AppIcon
        name="chevronDown"
        class="h-3.5 w-3.5 transition-transform text-muted-foreground shrink-0"
        :class="{ 'rotate-180': open }"
      />
    </button>

    <div
      v-if="open"
      class="absolute left-0 right-0 top-full z-50 mt-1 rounded-lg border border-border/50 bg-background/95 backdrop-blur-xl p-1 shadow-lg ring-1 ring-black/5"
    >
      <div class="max-h-[220px] overflow-y-auto custom-scrollbar pr-1 space-y-0.5">
        <div
          v-for="acc in accounts"
          :key="acc.id"
          @click="$emit('select', acc.id)"
          class="flex h-8 w-full items-center gap-2 rounded-lg px-2 text-left text-xs font-medium transition-colors hover:bg-accent cursor-pointer group/item"
          :class="selectedId === acc.id ? 'text-foreground bg-accent/50 font-semibold' : 'text-muted-foreground'"
        >
          <AppIcon name="rss" class="h-3.5 w-3.5 shrink-0 opacity-70" />
          <span class="flex-1 truncate">
            {{ acc.name }}
            <span class="text-[9px] text-muted-foreground/80 block">({{ acc.provider }})</span>
          </span>
          <div class="flex items-center gap-0.5 opacity-0 group-hover/item:opacity-100 transition-opacity">
            <button
              @click.stop="$emit('edit', acc)"
              class="h-7 w-7 rounded-md hover:bg-accent flex items-center justify-center text-muted-foreground hover:text-foreground transition-colors"
              title="编辑账号"
            >
              <AppIcon name="pencil" class="h-3.5 w-3.5" />
            </button>
            <button
              @click.stop="$emit('delete', acc)"
              class="h-7 w-7 rounded-md hover:bg-destructive/15 flex items-center justify-center text-muted-foreground hover:text-destructive transition-colors"
              title="删除账号"
            >
              <AppIcon name="trash" class="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
        <div v-if="!accounts.length" class="py-4 text-center text-xs text-muted-foreground">暂无账号</div>
        <div class="h-px w-full bg-border/50 my-1"></div>
        <button
          @click="$emit('add')"
          class="flex h-9 w-full items-center justify-center gap-2 rounded-lg px-3 text-sm font-semibold text-primary hover:bg-primary/5 transition-colors"
        >
          <AppIcon name="plus" class="h-4 w-4" />
          添加服务账号
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'
import type { RssAccount } from '@/composables/rssTypes'

defineProps<{
  accounts: RssAccount[]
  selectedId: number | null
  selectedName: string
  open: boolean
}>()

defineEmits<{
  toggle: []
  select: [id: number]
  edit: [acc: RssAccount]
  delete: [acc: RssAccount]
  add: []
}>()
</script>
