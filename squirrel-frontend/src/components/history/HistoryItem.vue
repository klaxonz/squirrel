<template>
  <article class="history-item-row">
    <button type="button" class="history-item-row__primary" @click="$emit('open', video)">
      <div class="history-item-row__thumb">
        <div class="history-item-row__thumb-fallback">
          <Icon icon="lucide:film" />
        </div>
        <img
          v-if="video.thumbnail"
          :src="video.thumbnail"
          referrerpolicy="no-referrer"
          :alt="video.title"
          @error="handleThumbnailError"
        />
        <span v-if="video.duration" class="history-item-row__duration">
          {{ formatDuration(video.duration) }}
        </span>
        <div v-if="video.progress > 0" class="history-item-row__progress">
          <div
            class="history-item-row__progress-fill"
            :style="{ width: `${video.progress * 100}%` }"
          ></div>
        </div>
      </div>

      <div class="history-item-row__body">
        <span class="history-item-row__title">{{ video.title }}</span>
        <span class="history-item-row__meta">
          <template v-if="displayAvatars.length">
            <SubscriptionAvatar
              v-for="(avatar, index) in displayAvatars"
              :key="`avatar-${index}`"
              :src="avatar.avatar"
              :name="avatar.name"
              size="xs"
              class="history-item-row__avatar"
            />
          </template>

          <span v-if="displayChannel">{{ displayChannel }}</span>

          <span class="history-item-row__meta-dot" aria-hidden="true"></span>

          <span v-if="video.progress > 0" class="history-item-row__progress-text">
            {{ (video.progress * 100).toFixed(0) }}%
          </span>

          <span class="history-item-row__meta-dot" aria-hidden="true"></span>

          <span>{{ formatDate(video.played_at) }}</span>
        </span>
      </div>
    </button>

    <button
      type="button"
      class="history-item-row__remove"
      title="从历史记录中移除"
      @click.stop="handleDelete"
    >
      <Icon icon="lucide:x" />
    </button>

    <Dialog :open="showDeleteConfirm" @update:open="showDeleteConfirm = $event">
      <DialogContent class="max-w-sm">
        <DialogHeader>
          <DialogTitle>移除历史记录</DialogTitle>
          <DialogDescription>
            确定要移除这条播放记录吗？
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button variant="secondary" size="sm" @click="showDeleteConfirm = false">取消</Button>
          <Button variant="destructive" size="sm" @click="confirmDelete">确认移除</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Icon } from '@iconify/vue'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { formatDate, formatDuration } from '@/utils/dateFormat'

const props = defineProps({
  video: {
    type: Object,
    required: true
  }
})

const emit = defineEmits(['open', 'delete'])

const showDeleteConfirm = ref(false)

const handleThumbnailError = (e) => {
  e.target.style.display = 'none'
}

const handleDelete = () => {
  showDeleteConfirm.value = true
}

const confirmDelete = () => {
  emit('delete', props.video.history_id ?? props.video.id)
  showDeleteConfirm.value = false
}

const displayAvatars = computed(() => {
  let avatars = props.video.subscriptions?.map((s) => ({
    id: s.id,
    name: s.name,
    avatar: s.avatar,
  })) || []

  if (!avatars.length && props.video.actors) {
    avatars = props.video.actors.map((a) => ({
      id: a.id,
      name: a.name,
      avatar: a.avatar,
    }))
  }

  return avatars.slice(0, 3)
})

const displayChannel = computed(() => {
  if (props.video.subscriptions?.length) {
    return props.video.subscriptions.map(s => s.name).join(' / ')
  }
  return ''
})
</script>

<style scoped>
.history-item-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 0.4rem;
  align-items: center;
  padding: 0;
  border-radius: var(--radius-md);
  transition: background 0.15s ease;
}

.history-item-row:hover {
  background: hsl(var(--secondary) / 0.15);
}

.history-item-row__primary {
  width: 100%;
  display: grid;
  grid-template-columns: 7.5rem minmax(0, 1fr);
  gap: 0.7rem;
  align-items: center;
  border: none;
  background: transparent;
  text-align: left;
  padding: 0.5rem 0.4rem;
  cursor: pointer;
}

.history-item-row__thumb {
  position: relative;
  width: 7.5rem;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  border-radius: var(--radius-sm);
  background: hsl(var(--secondary) / 0.75);
  flex-shrink: 0;
}

.history-item-row__thumb-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: hsl(var(--muted-foreground));
  font-size: 1.1rem;
}

.history-item-row__thumb img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.history-item-row__duration {
  position: absolute;
  bottom: 4px;
  right: 4px;
  padding: 0.1rem 0.35rem;
  border-radius: calc(var(--radius-sm) - 2px);
  background: rgb(0 0 0 / 0.75);
  color: #fff;
  font-size: 0.62rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  line-height: 1.3;
}

.history-item-row__progress {
  position: absolute;
  bottom: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: rgba(255, 255, 255, 0.15);
  z-index: 1;
}

.history-item-row__progress-fill {
  height: 100%;
  background: hsl(var(--primary));
  box-shadow: 0 0 6px hsl(var(--primary) / 0.8);
}

.history-item-row__body {
  min-width: 0;
  display: grid;
  gap: 0.25rem;
  align-content: center;
}

.history-item-row__title {
  color: hsl(var(--foreground));
  font-size: 0.84rem;
  font-weight: 600;
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.history-item-row__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.66rem;
}

.history-item-row__meta-dot {
  width: 0.2rem;
  height: 0.2rem;
  border-radius: 999px;
  background: hsl(var(--border));
}

.history-item-row__avatar {
  width: 1rem;
  height: 1rem;
  border-radius: calc(var(--radius-sm) - 1px);
  margin-right: -0.25rem;
  border: 1px solid hsl(var(--background));
}

.history-item-row__progress-text {
  color: hsl(var(--primary) / 0.8);
  font-weight: 500;
}

.history-item-row__remove {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: hsl(var(--muted-foreground));
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s ease, background 0.15s ease, color 0.15s ease;
  margin-right: 0.1rem;
}

.history-item-row:hover .history-item-row__remove,
.history-item-row__remove:focus-visible {
  opacity: 1;
}

.history-item-row__remove:hover {
  background: hsl(var(--destructive) / 0.1);
  color: hsl(var(--destructive));
}

@media (max-width: 767px) {
  .history-item-row__primary {
    grid-template-columns: 5.5rem minmax(0, 1fr);
    gap: 0.5rem;
  }

  .history-item-row__thumb {
    width: 5.5rem;
  }

  .history-item-row__remove {
    opacity: 1;
  }
}

@media (hover: none) {
  .history-item-row__remove {
    opacity: 1;
  }
}
</style>
