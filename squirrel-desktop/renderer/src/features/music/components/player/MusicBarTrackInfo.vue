<template>
  <Button
    text severity="secondary"
    class="music-bar-track-info"
    :class="{ 'music-bar-track-info--clickable': clickable }"
    @click="clickable && $emit('click')"
  >
    <div class="music-bar-cover">
      <img
        v-if="track?.cover"
        :src="track.cover"
        alt=""
        class="h-full w-full object-cover"
      />
      <AppIcon v-else name="playlistMusic" class="h-4 w-4" />
    </div>
    <div class="music-bar-text">
      <span class="music-bar-title">{{ track?.title || '未在播放' }}</span>
      <!-- Short recoverable label — full detail on title; auth opens login. -->
      <span
        v-if="error"
        class="music-bar-error"
        :class="{ 'music-bar-error--action': needsRelogin }"
        :title="error"
        :role="needsRelogin ? 'link' : undefined"
        @click.stop="onErrorAction"
      >{{ shortError }}</span>
      <span v-else class="music-bar-artist">{{ track?.artist || '酷狗音乐' }}</span>
    </div>
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

/** Keep the third of the player bar readable (Spec 3). */
const shortError = computed(() => {
  const raw = String(props.error || '').trim()
  if (!raw) return ''
  if (needsRelogin.value) return '需重新登录 · 点此登录'
  if (/网络|timeout|fetch|连接/i.test(raw)) return '网络异常，请重试'
  if (raw.length <= 18) return raw
  return '播放失败，请重试'
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
  gap: 0.625rem;
  border-radius: var(--radius-md);
  padding: 0.25rem 0.375rem 0.25rem 0.25rem;
  color: inherit;
  text-align: left;
  cursor: default;
}

.music-bar-track-info--clickable {
  cursor: pointer;
}

.music-bar-cover {
  display: flex;
  width: 2.25rem;
  height: 2.25rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border-radius: var(--radius-md);
  background: hsl(var(--muted) / 0.4);
  color: hsl(var(--muted-foreground));
}

.music-bar-text {
  flex: 1;
  min-width: 0;
}

.music-bar-title {
  display: block;
  font-size: 0.8125rem;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-bar-artist {
  display: block;
  font-size: 0.6875rem;
  color: hsl(var(--muted-foreground));
  margin-top: 0.125rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-bar-error {
  display: block;
  margin-top: 0.125rem;
  overflow: hidden;
  color: hsl(var(--destructive));
  font-size: 0.6875rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.music-bar-error--action {
  text-decoration: underline;
  text-underline-offset: 0.125rem;
  cursor: pointer;
}
</style>
