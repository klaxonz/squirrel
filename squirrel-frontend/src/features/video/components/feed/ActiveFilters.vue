<template>
  <div v-if="activeChips.length > 0" class="active-filters" aria-label="已启用的筛选条件">
    <span class="active-filters__label">已筛选</span>
    <div class="active-filters__chips">
      <Button
        v-for="chip in activeChips"
        :key="chip.key"
        type="button"
        variant="outline"
        size="xs"
        class="app-toolbar-chip app-toolbar-chip--active active-filters__chip"
        :title="`移除 ${chip.label} 筛选`"
        @click="$emit('remove', chip.key)"
      >
        <span class="truncate">{{ chip.label }}</span>
        <AppIcon name="close" class="size-3 shrink-0 opacity-60" />
      </Button>
      <Button
        type="button"
        variant="ghost"
        size="xs"
        class="active-filters__clear"
        @click="$emit('clearAll')"
      >
        清除
      </Button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
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

<style scoped>
.active-filters {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.active-filters__label {
  flex-shrink: 0;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 600;
}

.active-filters__chips {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.375rem;
}

.active-filters__chip {
  max-width: 12rem;
}

.active-filters__chip:hover {
  border-color: hsl(var(--destructive) / 0.3);
  background: hsl(var(--destructive) / 0.08);
  color: hsl(var(--destructive));
}

.active-filters__clear {
  color: hsl(var(--muted-foreground));
  font-weight: 600;
}

.active-filters__clear:hover {
  color: hsl(var(--foreground));
}
</style>
