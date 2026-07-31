<template>
  <section class="music-home-controls" aria-label="音乐快捷控制">
    <div class="music-home-controls__fm">
      <span class="music-home-controls__icon" aria-hidden="true">
        <AppIcon :name="fmPlaying ? 'volumeHigh' : 'playlistMusic'" />
      </span>
      <div class="music-home-controls__copy">
        <strong>私人 FM</strong>
        <span aria-live="polite">{{ fmStateText }}</span>
      </div>
      <Button
        size="sm"
        :loading="fmLoading"
        :aria-label="fmButtonTitle"
        :title="fmButtonTitle"
        @click="$emit('fm-play')"
      >
        <AppIcon v-if="!fmLoading" :name="fmPlaying ? 'pause' : 'play'" class="size-3.5" />
        {{ fmPlaying ? '暂停' : fmActive ? '继续' : '开始' }}
      </Button>
    </div>

    <div class="music-home-controls__tools">
      <div class="music-home-controls__preferences">
        <label class="music-home-controls__preference">
          <span>模式</span>
          <AppSegmentedControl
            :model-value="fmMode"
            :options="fmModes"
            size="sm"
            aria-label="私人 FM 模式"
            @update:model-value="$emit('switch-fm-mode', $event as FmMode)"
          />
        </label>
        <label class="music-home-controls__preference">
          <span>曲库</span>
          <AppSegmentedControl
            :model-value="fmPoolId"
            :options="fmPools"
            size="sm"
            aria-label="私人 FM 曲库"
            @update:model-value="$emit('switch-fm-pool', String($event))"
          />
        </label>
      </div>

      <nav class="music-home-controls__shortcuts" aria-label="音乐快捷入口">
        <Button text severity="secondary" size="sm" @click="$emit('everyday')">
          <AppIcon name="time" class="size-3.5" />
          每日推荐
        </Button>
        <Button text severity="secondary" size="sm" @click="$emit('new-songs')">
          <AppIcon name="playlistMusic" class="size-3.5" />
          新歌速递
        </Button>
      </nav>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSegmentedControl from '@/shared/components/layout/AppSegmentedControl.vue'
import { Button } from '@/shared/ui/button'

type FmMode = 'normal' | 'small' | 'peak'

const props = defineProps<{
  fmMode: FmMode
  fmPoolId: string
  fmLoading?: boolean
  fmActive?: boolean
  fmPlaying?: boolean
}>()

defineEmits<{
  'fm-play': []
  everyday: []
  'new-songs': []
  'switch-fm-mode': [mode: FmMode]
  'switch-fm-pool': [poolId: string]
}>()

const fmModes = [
  { value: 'normal', label: '发现' },
  { value: 'small', label: '小众' },
  { value: 'peak', label: '30s' },
] as const

const fmPools = [
  { value: '0', label: '口味' },
  { value: '1', label: '风格' },
  { value: '2', label: 'Gamma' },
] as const

const currentModeLabel = computed(() => fmModes.find(item => item.value === props.fmMode)?.label || '发现')
const currentPoolLabel = computed(() => fmPools.find(item => item.value === props.fmPoolId)?.label || '口味')

const fmStateText = computed(() => {
  const preference = `${currentModeLabel.value} · ${currentPoolLabel.value}`
  if (props.fmLoading) return `正在载入 · ${preference}`
  if (props.fmPlaying) return `正在播放 · ${preference}`
  if (props.fmActive) return `已暂停 · ${preference}`
  return preference
})

const fmButtonTitle = computed(() => {
  if (props.fmLoading) return '正在加载私人 FM'
  if (props.fmPlaying) return '暂停私人 FM'
  if (props.fmActive) return '继续私人 FM'
  return '播放私人 FM'
})
</script>

<style scoped>
.music-home-controls {
  display: grid;
  min-width: 0;
  grid-template-columns: minmax(16rem, 0.8fr) minmax(0, 1.2fr);
  align-items: center;
  gap: clamp(var(--space-5), 2.5vw, var(--space-8));
  margin-bottom: var(--space-7);
  border-bottom: 1px solid var(--app-hairline);
  padding: var(--space-3) 0 var(--space-4);
}

.music-home-controls__fm {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.music-home-controls__icon {
  display: inline-flex;
  width: 2.25rem;
  height: 2.25rem;
  flex: none;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.5);
  color: hsl(var(--muted-foreground));
}

.music-home-controls__icon svg {
  width: 0.9375rem;
  height: 0.9375rem;
}

.music-home-controls__copy {
  display: grid;
  min-width: 0;
  flex: 1;
  gap: 0.1rem;
}

.music-home-controls__copy strong {
  font-family: var(--app-heading-font);
  font-size: 0.875rem;
  font-weight: 650;
}

.music-home-controls__copy span,
.music-home-controls__preference > span {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

.music-home-controls__tools {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-4);
}

.music-home-controls__preferences {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.music-home-controls__preference {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.music-home-controls__shortcuts {
  display: flex;
  flex: none;
  align-items: center;
  gap: var(--space-1);
  border-left: 1px solid var(--app-hairline);
  padding-left: var(--space-3);
}

@media (max-width: 1120px) {
  .music-home-controls {
    grid-template-columns: minmax(0, 1fr);
    gap: var(--space-3);
  }

  .music-home-controls__tools {
    justify-content: space-between;
  }
}

@media (max-width: 720px) {
  .music-home-controls__tools,
  .music-home-controls__preferences {
    align-items: flex-start;
    flex-direction: column;
  }

  .music-home-controls__shortcuts {
    border-left: 0;
    padding-left: 0;
  }
}
</style>
