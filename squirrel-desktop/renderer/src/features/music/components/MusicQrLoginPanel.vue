<template>
  <div class="music-login-showcase">
    <div class="music-login-content">
      <template v-if="!qrOpen">
        <div class="music-login-art">
          <div class="music-login-art-circle music-login-art-circle--1"></div>
          <div class="music-login-art-circle music-login-art-circle--2"></div>
          <div class="music-login-art-circle music-login-art-circle--3"></div>
          <div class="music-login-icon-wrapper">
            <AppIcon name="playlistMusic" class="h-10 w-10 text-primary" />
          </div>
        </div>

        <h3 class="music-login-title">开启您的酷狗音乐之旅</h3>
        <p class="music-login-subtitle">
          登录后即可同步您在酷狗音乐创建的歌单与收藏，解锁海量曲库，更有个性化每日推荐、最近播放历史及听歌排行榜等专属特权。
        </p>

        <div class="music-login-actions">
          <Button size="lg" class="music-login-primary-action" @click="$emit('open')">
            <AppIcon name="user" class="h-4 w-4 mr-2" />
            立即扫码登录
          </Button>
        </div>
      </template>

      <template v-else>
        <div class="music-login-qr-inline">
          <div class="music-login-qr-header">
            <Button text severity="secondary" size="sm" icon-only title="返回" @click="$emit('close')">
              <AppIcon name="chevronLeft" class="h-4 w-4" />
            </Button>

            <div class="text-center flex-1">
              <h4 class="music-login-qr-title">扫码登录酷狗</h4>
              <p class="mt-0.5 flex items-center justify-center gap-1 text-xs font-medium text-muted-foreground">
                <span class="inline-block h-2.5 w-0.5 rounded-sm bg-success/50"></span>
                {{ qrStatusText }}
              </p>
            </div>

            <Button text severity="secondary" size="sm" icon-only :loading="qrLoading" title="刷新二维码" @click="$emit('refresh')">
              <AppIcon v-if="!qrLoading" name="refresh" class="h-4 w-4" />
            </Button>
          </div>

          <div class="music-login-qr-body">
            <div class="music-qr-card" :class="{ 'qr-expired': isExpired }" @click="isExpired && $emit('refresh')">
              <img v-if="qrLogin?.base64" :src="qrLogin.base64" alt="KuGou login QR code" class="music-qr-img" :style="{ opacity: isExpired ? 0.15 : 1, filter: isExpired ? 'blur(3px)' : 'none' }" />
              <AppSpinner v-else size="lg" class="text-primary" />

              <div v-if="isExpired" class="music-qr-expired-overlay">
                <AppIcon name="refresh" class="h-5 w-5 text-primary mb-1 animate-pulse" />
                <span class="music-qr-expired-title">二维码已失效</span>
                <span class="mt-0.5 text-xs text-muted-foreground">点击重试</span>
              </div>
            </div>

            <p class="text-xs text-muted-foreground max-w-[14rem] leading-relaxed mt-1">
              请使用酷狗音乐 App 扫描上方二维码
            </p>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { MusicQrLogin } from '@/shared/api/music'

const props = defineProps<{
  qrOpen: boolean
  qrLoading: boolean
  qrLogin: MusicQrLogin | null
  qrStatus: number
  qrStatusText: string
}>()

const isExpired = computed(() => props.qrStatus === 0 && !!props.qrLogin)

defineEmits<{
  'open': []
  'close': []
  'refresh': []
}>()
</script>

<style scoped>
.music-login-showcase {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 3rem;
  min-height: 400px;
}

.music-login-content {
  max-width: 24rem;
  text-align: center;
}

.music-login-art {
  position: relative;
  width: 160px;
  height: 160px;
  margin: 0 auto 1.5rem;
}

.music-login-icon-wrapper {
  position: absolute;
  inset: 4.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border) / 0.72);
  border-radius: var(--radius-lg);
}

.music-login-title {
  font-size: 1.25rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
  color: hsl(var(--foreground));
}

.music-login-subtitle {
  font-size: 0.875rem;
  color: hsl(var(--muted-foreground));
  line-height: 1.6;
  margin-bottom: 1.5rem;
}

.music-login-actions {
  display: flex;
  justify-content: center;
}

.music-login-primary-action {
  font-weight: 600;
}

.music-login-qr-inline {
  width: 100%;
}

.music-login-qr-header {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}

.music-login-qr-title {
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.4;
  color: hsl(var(--foreground));
}

.music-login-qr-body {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.music-qr-card {
  width: 200px;
  height: 200px;
  /* 二维码需要纯白底才能被扫描，保持白色不随主题 */
  background: white;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

.music-qr-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.music-qr-expired-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: hsl(var(--card) / 0.92);
  cursor: pointer;
}

.music-qr-expired-title {
  font-size: 0.75rem;
  font-weight: 600;
  color: hsl(var(--foreground));
}
</style>
