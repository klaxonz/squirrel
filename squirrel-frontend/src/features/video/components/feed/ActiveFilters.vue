<template>
  <div v-if="activeChips.length > 0" class="flex min-w-0 flex-wrap items-center gap-2">
    <span class="shrink-0 text-xs font-medium text-muted-foreground">已筛选</span>
    <div class="flex min-w-0 flex-wrap items-center gap-1.5">
      <button
        v-for="chip in activeChips"
        :key="chip.key"
        type="button"
        class="inline-flex h-7 max-w-[12rem] items-center gap-1.5 rounded-md border border-border/50 bg-muted/35 px-2.5 text-xs font-medium text-foreground transition-colors hover:border-destructive/30 hover:bg-destructive/10 hover:text-destructive"
        :title="`移除 ${chip.label} 筛选`"
        @click="$emit('remove', chip.key)"
      >
        <span class="truncate">{{ chip.label }}</span>
        <AppIcon name="close" class="size-3 shrink-0 opacity-60" />
      </button>
      <button
        type="button"
        class="inline-flex h-7 items-center rounded-md px-2 text-xs font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        @click="$emit('clearAll')"
      >
        清除
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import type { TimeRange, Duration, ContentType } from '@/features/video/composables/useFeedFilters'

const props = defineProps<{
  site?: string
  nsfw?: string
  timeRange?: TimeRange
  duration?: Duration
  contentType?: ContentType
  siteLabel?: string
}>()

defineEmits<{
  remove: [key: string]
  clearAll: []
}>()

const timeRangeLabels: Record<TimeRange, string> = {
  all: '',
  today: '今天',
  week: '本周',
  month: '本月',
  year: '本年',
}

const durationLabels: Record<Duration, string> = {
  all: '',
  short: '短片',
  medium: '常规',
  long: '长片',
}

const contentTypeLabels: Record<string, string> = {
  all: '',
  CHANNEL: '频道',
  PLAYLIST: '列表',
  ACTRESS: '女優',
  MOVIE: '电影',
  TV_SERIES: '剧集',
  ACTOR: '演员',
}

const nsfwLabels: Record<string, string> = {
  all: '',
  yes: '敏感',
  no: '安全',
}

const activeChips = computed(() => {
  const chips: { key: string, label: string }[] = []

  if (props.site && props.siteLabel) chips.push({ key: 'site', label: props.siteLabel })
  if (props.nsfw && props.nsfw !== 'all') chips.push({ key: 'nsfw', label: nsfwLabels[props.nsfw] || props.nsfw })
  if (props.timeRange && props.timeRange !== 'all') chips.push({ key: 'timeRange', label: timeRangeLabels[props.timeRange] })
  if (props.duration && props.duration !== 'all') chips.push({ key: 'duration', label: durationLabels[props.duration] })
  if (props.contentType && props.contentType !== 'all') chips.push({ key: 'contentType', label: contentTypeLabels[props.contentType] || props.contentType })

  return chips
})
</script>
