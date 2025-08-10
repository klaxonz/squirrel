<template>
  <div class="playback-controls">
    <!-- 播放/暂停按钮 -->
    <button 
      @click="$emit('toggle-play')" 
      class="control-btn play-btn" 
      :aria-label="playing ? '暂停' : '播放'"
    >
      <Icon 
        v-if="playing" 
        icon="material-symbols:pause" 
        class="control-icon" 
      />
      <Icon 
        v-else 
        icon="material-symbols:play-arrow" 
        class="control-icon" 
      />
    </button>

    <!-- 跳过按钮组 -->
    <div class="skip-controls">
      <button 
        @click="$emit('skip-backward')" 
        class="control-btn skip-btn" 
        aria-label="后退10秒"
      >
        <Icon icon="material-symbols:replay-10" class="control-icon" />
      </button>
      
      <button 
        @click="$emit('skip-forward')" 
        class="control-btn skip-btn" 
        aria-label="前进10秒"
      >
        <Icon icon="material-symbols:forward-10" class="control-icon" />
      </button>
    </div>
  </div>
</template>

<script setup>
import { Icon } from '@iconify/vue'

const props = defineProps({
  playing: Boolean
})

const emit = defineEmits(['toggle-play', 'skip-forward', 'skip-backward'])
</script>

<style scoped>
.playback-controls {
  @apply flex items-center gap-1;
}

.control-btn {
  @apply p-2 rounded-lg bg-black/20 hover:bg-black/40 
    transition-colors duration-200 text-white
    focus:outline-none focus:ring-2 focus:ring-white/50;
}

.play-btn {
  @apply p-3;
}

.skip-controls {
  @apply flex items-center gap-1;
}

.skip-btn {
  @apply p-1.5;
}

.control-icon {
  @apply text-lg;
}

.play-btn .control-icon {
  @apply text-xl;
}

.skip-btn .control-icon {
  @apply text-base;
}
</style>
