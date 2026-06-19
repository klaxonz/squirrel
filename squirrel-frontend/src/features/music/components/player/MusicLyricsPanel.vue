<template>
  <div class="music-lyrics-panel">
    <div v-if="loading" class="music-lyrics-state">
      <AppSpinner size="lg" />
      <span>歌词加载中...</span>
    </div>
    <div v-else-if="error" class="music-lyrics-state text-destructive">
      <span>{{ error }}</span>
    </div>
    <AppEmptyState v-else-if="!lines.length" variant="plain" title="暂无歌词" />
    <div v-else ref="scrollRef" class="music-lyrics-scrollable">
      <p
        v-for="(line, index) in lines"
        :key="`${line.time}-${index}`"
        class="music-lyric-line"
        :class="{ 'music-lyric-line--active': index === currentIndex }"
        @click="$emit('seek', line.time)"
      >
        {{ line.text || '·' }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import type { MusicLyricLine } from '@/shared/api/music'

const props = defineProps<{
  lines: MusicLyricLine[]
  currentIndex: number
  loading?: boolean
  error?: string
}>()

defineEmits<{
  seek: [time: number]
}>()

const scrollRef = ref<HTMLElement | null>(null)

watch(
  () => [props.currentIndex, props.lines.length],
  async ([idx]) => {
    if (idx === -1) return
    await nextTick()

    const container = scrollRef.value
    const activeEl = container?.querySelector<HTMLElement>('.music-lyric-line--active')
    if (!container || !activeEl) return

    const top = activeEl.offsetTop - (container.clientHeight - activeEl.offsetHeight) / 2
    container.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
  },
  { immediate: true, flush: 'post' },
)
</script>

<style scoped>
.music-lyrics-panel {
  flex: 1;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 10%,
    black 90%,
    transparent 100%
  );
  -webkit-mask-image: linear-gradient(
    to bottom,
    transparent 0%,
    black 10%,
    black 90%,
    transparent 100%
  );
  padding: 3rem 1rem;
}

.music-lyrics-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 0.75rem;
  color: hsl(var(--foreground) / 0.45);
  font-size: 1rem;
}

.music-lyrics-scrollable {
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  padding: 1rem 0;
  scrollbar-width: none;
}

.music-lyrics-scrollable::-webkit-scrollbar {
  display: none;
}

.music-lyric-line {
  font-size: 1.25rem;
  font-weight: 600;
  line-height: 1.6;
  color: hsl(var(--foreground) / 0.35);
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  text-align: center;
}

.music-lyric-line:hover {
  color: hsl(var(--foreground) / 0.7);
}

.music-lyric-line--active {
  color: hsl(var(--foreground)) !important;
  font-size: 1.5rem;
  font-weight: 700;
}

@media (max-width: 768px) {
  .music-lyric-line {
    font-size: 1rem;
  }

  .music-lyric-line--active {
    font-size: 1.25rem;
  }
}
</style>
