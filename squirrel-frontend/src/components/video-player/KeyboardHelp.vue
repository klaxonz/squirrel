<template>
  <div class="keyboard-help-overlay" @click="$emit('close')">
    <div class="keyboard-help-modal" @click.stop>
      <div class="keyboard-help-header">
        <h3>键盘快捷键</h3>
        <button @click="$emit('close')" class="close-help-btn">
          <Icon icon="material-symbols:close" />
        </button>
      </div>

      <div class="keyboard-help-content">
        <div class="shortcut-section">
          <h4>播放控制</h4>
          <div class="shortcut-list">
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>空格</kbd> 或 <kbd>K</kbd>
              </div>
              <span>播放/暂停</span>
            </div>
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>←</kbd> / <kbd>→</kbd>
              </div>
              <span>快退/快进 5秒</span>
            </div>
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>J</kbd> / <kbd>L</kbd>
              </div>
              <span>快退/快进 10秒</span>
            </div>
          </div>
        </div>

        <div class="shortcut-section">
          <h4>音量控制</h4>
          <div class="shortcut-list">
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>M</kbd>
              </div>
              <span>静音/取消静音</span>
            </div>
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>↑</kbd> / <kbd>↓</kbd>
              </div>
              <span>音量 +5% / -5%</span>
            </div>
          </div>
        </div>

        <div class="shortcut-section">
          <h4>播放速度</h4>
          <div class="shortcut-list">
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>&lt;</kbd> / <kbd>&gt;</kbd>
              </div>
              <span>减慢/加快播放速度</span>
            </div>
          </div>
        </div>

        <div class="shortcut-section">
          <h4>其他功能</h4>
          <div class="shortcut-list">
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>F</kbd>
              </div>
              <span>全屏/退出全屏</span>
            </div>
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>I</kbd>
              </div>
              <span>画中画</span>
            </div>
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>C</kbd>
              </div>
              <span>字幕开/关</span>
            </div>
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>0-9</kbd>
              </div>
              <span>跳转到 0%-90%</span>
            </div>
            <div class="shortcut-item">
              <div class="shortcut-keys">
                <kbd>?</kbd>
              </div>
              <span>显示此帮助</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const emit = defineEmits(['close'])
</script>

<style scoped>
.keyboard-help-overlay {
  @apply fixed inset-0 bg-black/80 backdrop-blur-sm z-50
    flex items-center justify-center p-4;
}

.keyboard-help-modal {
  @apply bg-black/90 backdrop-blur-sm rounded-lg p-6 max-w-2xl w-full
    border border-white/10 shadow-xl max-h-[80vh] overflow-y-auto;
}

.keyboard-help-header {
  @apply flex items-center justify-between mb-6 pb-4 border-b border-white/10;
}

.keyboard-help-header h3 {
  @apply text-white text-xl font-semibold;
}

.close-help-btn {
  @apply p-2 rounded-lg bg-white/10 hover:bg-white/20 
    transition-colors duration-200 text-white;
}

.keyboard-help-content {
  @apply grid grid-cols-1 md:grid-cols-2 gap-6;
}

.shortcut-section {
  @apply space-y-3;
}

.shortcut-section h4 {
  @apply text-white font-medium text-lg mb-3;
}

.shortcut-list {
  @apply space-y-2;
}

.shortcut-item {
  @apply flex items-center justify-between gap-4;
}

.shortcut-keys {
  @apply flex items-center gap-1 flex-shrink-0;
}

.shortcut-item kbd {
  @apply inline-block px-2 py-1 text-xs font-mono
    bg-white/10 border border-white/20 rounded
    text-white min-w-6 text-center;
}

.shortcut-item span {
  @apply text-white/80 text-sm;
}

/* 动画效果 */
.keyboard-help-overlay {
  animation: overlay-appear 0.2s ease-out;
}

.keyboard-help-modal {
  animation: modal-appear 0.3s ease-out;
}

@keyframes overlay-appear {
  0% {
    opacity: 0;
  }
  100% {
    opacity: 1;
  }
}

@keyframes modal-appear {
  0% {
    opacity: 0;
    transform: scale(0.9) translateY(-20px);
  }
  100% {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}
</style>
