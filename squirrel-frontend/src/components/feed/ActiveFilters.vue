<template>
  <div v-if="activeChips.length > 0" class="active-filters">
    <span class="active-filters__label">已选：</span>
    <div class="active-filters__chips">
      <button
        v-for="chip in activeChips"
        :key="chip.key"
        class="filter-chip"
        @click="$emit('remove', chip.key)"
        :title="`移除 ${chip.label} 筛选`"
      >
        {{ chip.label }}
        <svg class="chip-remove-icon" viewBox="0 0 16 16" fill="none" stroke="currentColor">
          <path d="M4 4l8 8M12 4l-8 8" stroke-width="1.5" stroke-linecap="round" />
        </svg>
      </button>
      <button class="clear-all-btn" @click="$emit('clearAll')">
        清除全部
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { TimeRange, Duration, ContentType } from '@/composables/useFeedFilters'

const props = defineProps<{
  site?: string
  nsfw?: string
  timeRange?: TimeRange
  duration?: Duration
  contentType?: ContentType
  siteLabel?: string
}>()

const emit = defineEmits<{
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
  short: '短视频',
  medium: '中视频',
  long: '长视频',
}

const contentTypeLabels: Record<string, string> = {
  all: '',
  CHANNEL: '频道',
  PLAYLIST: '播放列表',
  ACTRESS: '女優',
  MOVIE: '电影',
  TV_SERIES: '剧集',
  ACTOR: '演员',
}

const nsfwLabels: Record<string, string> = {
  all: '',
  yes: '仅 NSFW',
  no: '仅安全内容',
}

const activeChips = computed(() => {
  const chips: { key: string; label: string }[] = []

  if (props.site && props.siteLabel) {
    chips.push({ key: 'site', label: props.siteLabel })
  }
  if (props.nsfw && props.nsfw !== 'all') {
    chips.push({ key: 'nsfw', label: nsfwLabels[props.nsfw] || props.nsfw })
  }
  if (props.timeRange && props.timeRange !== 'all') {
    chips.push({ key: 'timeRange', label: timeRangeLabels[props.timeRange] })
  }
  if (props.duration && props.duration !== 'all') {
    chips.push({ key: 'duration', label: durationLabels[props.duration] })
  }
  if (props.contentType && props.contentType !== 'all') {
    chips.push({ key: 'contentType', label: contentTypeLabels[props.contentType] || props.contentType })
  }

  return chips
})
</script>

<style scoped>
.active-filters {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.active-filters__label {
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.6rem;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: hsl(var(--muted-foreground) / 0.4);
  flex-shrink: 0;
}

.active-filters__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
  align-items: center;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  padding: 0.2rem 0.5rem 0.2rem 0.625rem;
  border-radius: var(--radius-sm);
  border: 1px solid hsl(var(--primary) / 0.35);
  background: hsl(var(--primary) / 0.08);
  color: hsl(var(--foreground));
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.6rem;
  font-weight: 500;
  letter-spacing: 0.05em;
  cursor: pointer;
  transition: all 0.15s ease;
}

.filter-chip:hover {
  background: hsl(var(--destructive) / 0.1);
  border-color: hsl(var(--destructive) / 0.4);
  color: hsl(var(--destructive));
}

.chip-remove-icon {
  width: 10px;
  height: 10px;
  opacity: 0.6;
}

.filter-chip:hover .chip-remove-icon {
  opacity: 1;
}

.clear-all-btn {
  padding: 0.2rem 0.5rem;
  border-radius: var(--radius-sm);
  border: 1px solid hsl(var(--border) / 0.3);
  background: transparent;
  color: hsl(var(--muted-foreground) / 0.5);
  font-family: 'JetBrains Mono', 'Courier New', monospace;
  font-size: 0.55rem;
  font-weight: 500;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  cursor: pointer;
  transition: all 0.15s ease;
}

.clear-all-btn:hover {
  border-color: hsl(var(--destructive) / 0.4);
  color: hsl(var(--destructive));
}
</style>
