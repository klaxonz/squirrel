<template>
  <div
    v-if="isOpen"
    class="context-menu"
    :style="{ top: `${position.y}px`, left: `${position.x}px` }"
    @click.stop
  >
    <div class="context-menu__section">
      <button class="context-menu__item" @click="handleToggleRead(true)">
        <span class="context-menu__icon-wrap">
          <CheckIcon class="context-menu__icon" />
        </span>
        <span class="context-menu__label">标记为已读</span>
      </button>

      <button class="context-menu__item" @click="handleToggleRead(false)">
        <span class="context-menu__icon-wrap">
          <XMarkIcon class="context-menu__icon" />
        </span>
        <span class="context-menu__label">标记为未读</span>
      </button>
    </div>

    <div class="context-menu__divider"></div>

    <div class="context-menu__section">
      <button class="context-menu__item" @click="handleLiked">
        <span class="context-menu__icon-wrap">
          <HeartIcon
            v-if="video.is_liked === 1"
            class="context-menu__icon context-menu__icon--destructive"
          />
          <HandThumbDownIcon
            v-else-if="video.is_liked === 0"
            class="context-menu__icon context-menu__icon--warning"
          />
          <HeartIcon
            v-else
            class="context-menu__icon"
          />
        </span>
        <span class="context-menu__label">
          {{
            video.is_liked === 1 ? '已喜欢' :
            video.is_liked === 0 ? '不喜欢' :
            '喜欢'
          }}
        </span>
      </button>

      <button class="context-menu__item" @click="handleCopyVideoLink">
        <span class="context-menu__icon-wrap">
          <ClipboardDocumentIcon class="context-menu__icon" />
        </span>
        <span class="context-menu__label">复制链接</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import {
  CheckIcon,
  ClipboardDocumentIcon,
  HeartIcon,
  HandThumbDownIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'

const props = defineProps({
  position: {
    type: Object,
    required: true,
  },
  isOpen: {
    type: Boolean,
    required: true,
  },
  video: {
    type: Object,
    required: true,
  },
})

const emit = defineEmits([
  'close',
  'toggleReadStatus',
  'copyVideoLink',
  'toggleLike',
])

const handleToggleRead = (isRead) => {
  emit('toggleReadStatus', isRead)
}

const handleCopyVideoLink = async () => {
  await emit('copyVideoLink')
  emit('close')
}

const handleLiked = async () => {
  await emit('toggleLike', props.video)
  emit('close')
}

const handleClickOutside = (event) => {
  if (!event.target.closest('.context-menu')) {
    emit('close')
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.context-menu {
  position: fixed;
  z-index: 60;
  width: 13rem;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.82);
  border-radius: calc(var(--radius-xl) + 2px);
  background:
    linear-gradient(180deg, hsl(var(--card) / 0.98), hsl(var(--background) / 0.94));
  box-shadow: 0 26px 56px hsl(var(--surface-shadow) / 0.22);
  backdrop-filter: blur(18px);
  animation: context-menu-fade-in 0.18s ease-out;
}

.context-menu__section {
  padding: 0.35rem;
}

.context-menu__divider {
  height: 1px;
  margin: 0 0.65rem;
  background: hsl(var(--border) / 0.78);
}

.context-menu__item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.7rem;
  border-radius: calc(var(--radius-lg) - 2px);
  padding: 0.62rem 0.7rem;
  color: hsl(var(--foreground));
  transition: background-color 0.16s ease, transform 0.16s ease, color 0.16s ease;
}

.context-menu__item:hover {
  background: hsl(var(--accent) / 0.72);
  transform: translateX(2px);
}

.context-menu__icon-wrap {
  display: inline-flex;
  size: 1.75rem;
  align-items: center;
  justify-content: center;
  border-radius: 9999px;
  background: hsl(var(--secondary) / 0.9);
  color: hsl(var(--muted-foreground));
}

.context-menu__icon {
  width: 0.95rem;
  height: 0.95rem;
}

.context-menu__icon--destructive {
  color: hsl(var(--destructive));
}

.context-menu__icon--warning {
  color: hsl(32 82% 52%);
}

.context-menu__label {
  font-size: 0.84rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}

@keyframes context-menu-fade-in {
  from {
    opacity: 0;
    transform: translateY(6px) scale(0.98);
  }

  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
