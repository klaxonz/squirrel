<template>
  <div class="empty-container">
    <div class="empty-shell">
      <!-- 背景装饰网格 -->
      <div class="empty-grid" aria-hidden="true"></div>
      
      <div class="empty-content">
        <div class="icon-wrapper">
          <div class="pulse-ring"></div>
          <div class="pulse-ring delay-1"></div>
          <div class="status-icon flex items-center justify-center">
             <!-- Static fallback icon to avoid component resolution issues -->
             <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="opacity-20"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>
          </div>
        </div>
        
        <div class="text-group">
          <h4 class="status-title font-mono uppercase tracking-[0.3em]">{{ title }}</h4>
          <p class="status-desc text-muted-foreground/30 text-xs font-medium max-w-[200px] mx-auto mt-2">{{ message }}</p>
          <slot name="hint"></slot>
        </div>
      </div>
      
      <!-- 边角装饰 -->
      <div class="corner-bracket top-left"></div>
      <div class="corner-bracket top-right"></div>
      <div class="corner-bracket bottom-left"></div>
      <div class="corner-bracket bottom-right"></div>
      
      <!-- 底部状态条 -->
      <div class="status-footer absolute bottom-2 w-full text-center pointer-events-none">
        <span class="font-mono text-[8px] opacity-10 tracking-[0.2em]">SQR_终端空闲</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  title?: string
  message: string
}>(), {
  title: '系统就绪'
})
</script>

<style scoped>
.empty-container {
  padding: 1rem;
  width: 100%;
}

.empty-shell {
  position: relative;
  min-height: 180px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border: 1px dashed hsl(var(--foreground) / 0.03);
  background: hsl(var(--foreground) / 0.01);
  overflow: hidden;
}

.empty-grid {
  position: absolute;
  inset: 0;
  background-image: radial-gradient(hsl(var(--foreground) / 0.02) 1px, transparent 1px);
  background-size: 16px 16px;
  opacity: 0.5;
  pointer-events: none;
}

.empty-content {
  position: relative;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
  text-align: center;
}

.icon-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
}

.pulse-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border: 1px solid hsl(var(--foreground) / 0.05);
  border-radius: 50%;
  animation: pulse-out 4s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

.delay-1 {
  animation-delay: 2s;
}

@keyframes pulse-out {
  0% { transform: scale(0.8); opacity: 0; }
  50% { opacity: 0.3; }
  100% { transform: scale(2.5); opacity: 0; }
}

.status-title {
  font-size: 10px;
  font-weight: 900;
  color: hsl(var(--foreground) / 0.2);
}

.corner-bracket {
  position: absolute;
  width: 6px;
  height: 6px;
  border-color: hsl(var(--foreground) / 0.05);
  border-style: solid;
}

.top-left { top: 8px; left: 8px; border-width: 1px 0 0 1px; }
.top-right { top: 8px; right: 8px; border-width: 1px 1px 0 0; }
.bottom-left { bottom: 8px; left: 8px; border-width: 0 0 1px 1px; }
.bottom-right { bottom: 8px; right: 8px; border-width: 0 1px 1px 0; }
</style>
