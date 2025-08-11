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
  @apply rounded-xl p-6 max-w-2xl w-full
    border border-white/10 shadow-2xl max-h-[80vh] overflow-y-auto;
  background: rgba(40, 40, 40, 0.95);
  backdrop-filter: blur(12px);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
}

.keyboard-help-header {
  @apply flex items-center justify-between mb-6 pb-4 border-b border-white/10;
}

.keyboard-help-header h3 {
  @apply text-white text-xl font-semibold;
  font-family: 'Roboto', 'YouTube Noto', sans-serif;
}

.close-help-btn {
  @apply p-2 rounded-full bg-transparent hover:bg-white/10
    transition-all duration-200 text-white;
}

.keyboard-help-content {
  @apply grid grid-cols-1 md:grid-cols-2 gap-6;
}

.shortcut-section {
  @apply space-y-3;
}

.shortcut-section h4 {
  @apply text-white font-medium text-lg mb-3;
  font-family: 'Roboto', sans-serif;
}

.shortcut-list {
  @apply space-y-3;
}

.shortcut-item {
  @apply flex items-center justify-between gap-4 p-2 rounded-lg
    hover:bg-white/5 transition-colors duration-200;
}

.shortcut-keys {
  @apply flex items-center gap-2 flex-shrink-0;
}

.shortcut-item kbd {
  @apply inline-block px-3 py-1.5 text-xs font-mono
    rounded-lg text-white min-w-8 text-center
    transition-all duration-200;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.shortcut-item:hover kbd {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.3);
}

.shortcut-item span {
  @apply text-white/80 text-sm;
  font-family: 'Roboto', sans-serif;
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
