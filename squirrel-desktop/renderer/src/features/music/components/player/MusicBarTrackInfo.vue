<template>
  <Button
    variant="secondary"
    class="music-bar-track-info"
    :class="{ 'music-bar-track-info--clickable': clickable }"
    @click="clickable && $emit('click')"
  >
    <span class="music-bar-cover">
      <img
        v-if="track?.cover"
        :src="track.cover"
        alt=""
        class="h-full w-full object-cover"
      />
      <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
    </span>
    <span class="music-bar-text">
      <span class="music-bar-title">{{ track?.title || '未在播放' }}</span>
      <span class="music-bar-meta">
        <span class="music-bar-artist">{{ track?.artist || '酷狗音乐' }}</span>
        <span
          v-if="error"
          class="music-bar-error"
          :class="{ 'music-bar-error--action': needsRelogin }"
          :title="error"
          :role="needsRelogin ? 'link' : undefined"
          @click.stop="onErrorAction"
        >
          <AppIcon name="error" class="music-bar-error-icon" />
          <span class="music-bar-error-label">{{ shortError }}</span>
        </span>
      </span>
    </span>
  </Button>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { MusicTrack } from '@/shared/api/music'

const props = withDefaults(defineProps<{
  track?: MusicTrack | null
  clickable?: boolean
  error?: string
}>(), {
  clickable: false,
  error: '',
})

defineEmits<{
  click: []
}>()

const router = useRouter()

const needsRelogin = computed(() => /登录|会话|鉴权|auth|login|token/i.test(String(props.error || '')))

const shortError = computed(() => {
  const raw = String(props.error || '').trim()
  if (!raw) return ''
  if (needsRelogin.value) return '需重新登录'
  if (/网络|timeout|fetch|连接/i.test(raw)) return '网络异常'
  return '暂不可播'
})

const onErrorAction = () => {
  if (!needsRelogin.value) return
  void router.push({ name: 'Music', query: { view: 'profile' } })
}
</script>

<style scoped>
.music-bar-track-info {
  min-width: 0;
  width: 100%;
  max-width: 100%;
  justify-content: flex-start;
  height: 3.25rem;
  gap: var(--space-3);
  border-radius: var(--radius-md);
  padding: 0.25rem;
  color: inherit;
  text-align: left;
  cursor: default;
}

.music-bar-track-info :deep(.sq-button__content) {
  width: 100%;
  min-width: 0;
  justify-content: flex-start;
}

.music-bar-track-info--clickable {
  cursor: pointer;
}

.music-bar-cover {
  display: flex;
  width: 2.75rem;
  height: 2.75rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--muted-foreground));
}

.music-bar-text {
  display: block;
  flex: 1;
  min-width: 0;
}

.music-bar-title {
  display: block;
  font-size: var(--app-text-md);
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-bar-meta {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
  margin-top: 0.15rem;
}

.music-bar-artist {
  min-width: 0;
  overflow: hidden;
  font-size: var(--app-text-xs);
  color: hsl(var(--muted-foreground));
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-bar-error {
  display: inline-flex;
  flex: none;
  align-items: center;
  gap: 0.2rem;
  color: hsl(var(--destructive));
  font-size: var(--app-text-xs);
  white-space: nowrap;
}

.music-bar-error::before {
  width: 1px;
  height: 0.625rem;
  margin-right: 0.15rem;
  background: hsl(var(--border));
  content: '';
}

.music-bar-error-icon {
  width: 0.6875rem;
  height: 0.6875rem;
}

.music-bar-error--action {
  text-decoration: underline;
  text-underline-offset: 0.125rem;
  cursor: pointer;
}

@media (max-width: 800px) {
  .music-bar-error-label,
  .music-bar-error::before {
    display: none;
  }
}
</style>
