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
          <AppIcon name="check" class="context-menu__icon" />
        </span>
        <span class="context-menu__label">标记为已读</span>
      </button>

      <button class="context-menu__item" @click="handleToggleRead(false)">
        <span class="context-menu__icon-wrap">
          <AppIcon name="close" class="context-menu__icon" />
        </span>
        <span class="context-menu__label">标记为未读</span>
      </button>
    </div>

    <div class="context-menu__divider"></div>

    <div class="context-menu__section">
      <button class="context-menu__item" @click="handleLiked">
        <span class="context-menu__icon-wrap">
          <AppIcon
            v-if="video.is_liked === 1"
            name="heart"
            class="context-menu__icon context-menu__icon--destructive"
          />
          <AppIcon
            v-else-if="video.is_liked === 0"
            name="dislike"
            class="context-menu__icon context-menu__icon--warning"
          />
          <AppIcon
            v-else
            name="heart"
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
          <AppIcon name="clipboard" class="context-menu__icon" />
        </span>
        <span class="context-menu__label">复制链接</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, onUnmounted } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'

const props = defineProps({
  position: { type: Object, required: true },
  isOpen: { type: Boolean, required: true },
  video: { type: Object, required: true }
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
  width: 11.5rem;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.82);
  border-radius: calc(var(--radius-lg) + 2px);
  background: hsl(var(--popover) / 0.98);
  box-shadow: var(--shadow-popover);
  backdrop-filter: blur(8px);
  animation: context-menu-fade-in var(--duration-fast) var(--ease-default);
}

.context-menu__section {
  padding: 0.25rem;
}

.context-menu__divider {
  height: 1px;
  margin: 0 0.5rem;
  background: hsl(var(--border) / 0.78);
}

.context-menu__item {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.55rem;
  border-radius: calc(var(--radius-md) + 1px);
  padding: 0.5rem 0.55rem;
  color: hsl(var(--foreground));
  transition:
    background-color var(--duration-fast) var(--ease-default),
    color var(--duration-fast) var(--ease-default);
}

.context-menu__item:hover {
  background: hsl(var(--accent) / 0.72);
}

.context-menu__icon-wrap {
  display: inline-flex;
  size: 1.5rem;
  align-items: center;
  justify-content: center;
  border-radius: 0.5rem;
  background: hsl(var(--secondary) / 0.9);
  color: hsl(var(--muted-foreground));
}

.context-menu__icon {
  width: 0.85rem;
  height: 0.85rem;
}

.context-menu__icon--destructive {
  color: hsl(var(--destructive));
}

.context-menu__icon--warning {
  color: hsl(32 82% 52%);
}

.context-menu__label {
  font-size: 0.76rem;
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
