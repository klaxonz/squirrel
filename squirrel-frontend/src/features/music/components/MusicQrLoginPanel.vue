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
          <Button class="music-login-btn-premium font-bold tracking-wide" @click="$emit('open')">
            <AppIcon name="user" class="h-4 w-4 mr-2" />
            立即扫码登录
          </Button>
        </div>
      </template>

      <template v-else>
        <div class="music-login-qr-inline">
          <div class="music-login-qr-header">
            <button class="music-login-qr-back" @click="$emit('close')" title="返回">
              <AppIcon name="chevronLeft" class="h-4 w-4" />
            </button>
            
            <div class="text-center flex-1">
              <h4 class="text-base font-extrabold tracking-tight">扫码登录酷狗</h4>
              <p class="text-[10px] text-muted-foreground font-medium flex items-center justify-center gap-1 mt-0.5">
                <span class="inline-block h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                {{ qrStatusText }}
              </p>
            </div>

            <button class="music-login-qr-refresh" @click="$emit('refresh')" :disabled="qrLoading" title="刷新二维码">
              <AppIcon name="refresh" class="h-4 w-4" :class="{ 'animate-spin': qrLoading }" />
            </button>
          </div>

          <div class="music-login-qr-body">
            <div class="music-qr-card" :class="{ 'qr-expired': qrStatus === 0 }" @click="qrStatus === 0 && $emit('refresh')">
              <img v-if="qrLogin?.base64" :src="qrLogin.base64" alt="KuGou login QR code" class="music-qr-img" :style="{ opacity: qrStatus === 0 ? 0.15 : 1, filter: qrStatus === 0 ? 'blur(3px)' : 'none' }" />
              <AppIcon v-else name="loadingSpinner" class="h-6 w-6 animate-spin text-primary" />
              
              <div v-if="qrStatus === 0" class="music-qr-expired-overlay">
                <AppIcon name="refresh" class="h-5 w-5 text-primary mb-1 animate-pulse" />
                <span class="text-[10px] font-bold text-slate-700">二维码已失效</span>
                <span class="text-[9px] text-muted-foreground mt-0.5">点击重试</span>
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
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Button } from '@/shared/ui/button'
import type { MusicQrLogin } from '@/shared/api/music'

defineProps<{
  qrOpen: boolean
  qrLoading: boolean
  qrLogin: MusicQrLogin | null
  qrStatus: number
  qrStatusText: string
}>()

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

.music-login-art-circle {
  position: absolute;
  border-radius: 9999px;
  border: 1px solid hsl(var(--primary) / 0.2);
  animation: pulse-ring 3s ease-in-out infinite;
}

.music-login-art-circle--1 {
  inset: 0;
  animation-delay: 0s;
}

.music-login-art-circle--2 {
  inset: 1.5rem;
  animation-delay: 0.5s;
}

.music-login-art-circle--3 {
  inset: 3rem;
  animation-delay: 1s;
}

@keyframes pulse-ring {
  0%, 100% { opacity: 0.3; transform: scale(1); }
  50% { opacity: 0.6; transform: scale(1.05); }
}

.music-login-icon-wrapper {
  position: absolute;
  inset: 4.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: hsl(var(--card));
  border-radius: 9999px;
  box-shadow: 0 4px 12px hsl(var(--foreground) / 0.1);
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

.music-login-btn-premium {
  background: linear-gradient(135deg, hsl(var(--primary)), hsl(var(--primary) / 0.9));
  color: hsl(var(--primary-foreground));
  border: none;
  border-radius: 9999px;
  padding: 0.75rem 1.5rem;
}

.music-login-qr-inline {
  width: 100%;
}

.music-login-qr-header {
  display: flex;
  align-items: center;
  margin-bottom: 1rem;
}

.music-login-qr-back,
.music-login-qr-refresh {
  width: 2rem;
  height: 2rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: hsl(var(--muted) / 0.4);
  border-radius: 9999px;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
}

.music-login-qr-back:hover,
.music-login-qr-refresh:hover {
  background: hsl(var(--muted) / 0.6);
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
  background: white;
  border-radius: 0.75rem;
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
  background: hsl(var(--background) / 0.9);
  cursor: pointer;
}

.music-login-qr-inline .text-base {
  font-size: 1rem;
}
</style>
