<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="channel-header w-full">
      <div class="channel-header-content pt-4">
        <div class="flex items-start gap-4 pb-3">
          <div class="flex items-center min-w-0 flex-1">
            <img v-if="detail" :src="getAvatarSrc(detail.avatar, subscriptionId)" class="w-12 h-12 rounded-full object-cover mr-4" alt="avatar" referrerpolicy="no-referrer" @error="(e) => handleAvatarError(e, subscriptionId)" />
            <div class="min-w-0 flex-1">
              <div class="channel-header__title-row">
                <h2 class="channel-header__title">{{ detail?.name || '频道' }}</h2>
                <button
                  type="button"
                  class="channel-header__unsubscribe"
                  :disabled="isUnsubscribing"
                  :aria-busy="isUnsubscribing ? 'true' : 'false'"
                  @click="handleUnsubscribe"
                >
                  <span v-if="isUnsubscribing" class="channel-header__spinner" aria-hidden="true"></span>
                  <span>{{ isUnsubscribing ? '取消中' : '取消订阅' }}</span>
                </button>
                <span v-if="detail?.is_nsfw" class="text-2xs font-medium px-1.5 py-0.5 rounded bg-destructive/20 text-destructive">NSFW</span>
              </div>
              <div class="text-xs text-muted-foreground mt-0.5 truncate">
                <span class="mr-3">共 {{ detail?.total_videos || 0 }} 个视频</span>
                <span>已抓取 {{ detail?.total_extract || 0 }}</span>
              </div>
              <p v-if="unsubscribeError" class="channel-header__error">{{ unsubscribeError }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </transition>
  <transition name="channel-dismiss">
    <div v-if="detail?.description && isVisible" class="channel-description pb-3 text-sm text-muted-foreground">
      <p class="whitespace-pre-line line-clamp-3">{{ detail.description }}</p>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router'
import { useImageFallback } from '@/composables/useImageFallback'
import { getSubscriptionDetail, unsubscribe as apiUnsubscribe } from '@/api'

const props = defineProps({
  subscriptionId: { type: [String, Number], required: true }
});

const router = useRouter()
const detail = ref(null);
const loading = ref(false);
const isVisible = ref(true)
const isUnsubscribing = ref(false)
const unsubscribeError = ref('')
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();
const DISMISS_MS = 180

const wait = (ms) => new Promise((resolve) => {
  window.setTimeout(resolve, ms)
})

const fetchDetail = async () => {
  if (!props.subscriptionId) return;
  loading.value = true;
  const { data, error } = await getSubscriptionDetail(props.subscriptionId);
  if (!error) detail.value = data;
  loading.value = false;
};

const handleUnsubscribe = async () => {
  if (!props.subscriptionId || isUnsubscribing.value) return

  isUnsubscribing.value = true
  unsubscribeError.value = ''

  const { error } = await apiUnsubscribe(props.subscriptionId)

  if (error) {
    unsubscribeError.value = error?.message || '取消订阅失败'
    isUnsubscribing.value = false
    return
  }

  isVisible.value = false
  await wait(DISMISS_MS)
  router.back()
}

watch(() => props.subscriptionId, () => {
  isVisible.value = true
  isUnsubscribing.value = false
  unsubscribeError.value = ''
  fetchDetail()
}, { immediate: true });
</script>

<style scoped>
.channel-header { backdrop-filter: blur(6px); }

.channel-header-content,
.channel-description {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding: 0 1rem;
  width: 100%;
}

.channel-header__title-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 0;
  flex-wrap: wrap;
}

.channel-header__title {
  min-width: 0;
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
  line-height: 1.2;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.channel-header__unsubscribe {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.4rem;
  flex-shrink: 0;
  min-width: 5.2rem;
  min-height: 1.8rem;
  padding: 0 0.72rem;
  border: 1px solid hsl(var(--border) / 0.82);
  border-radius: 9999px;
  background: hsl(var(--background) / 0.8);
  color: hsl(var(--foreground));
  font-size: 0.7rem;
  font-weight: 600;
  transition: background-color 0.18s ease, border-color 0.18s ease, opacity 0.18s ease, transform 0.18s ease;
}

.channel-header__unsubscribe:hover:not(:disabled) {
  background: hsl(var(--accent));
  border-color: hsl(var(--ring) / 0.28);
  transform: translateY(-1px);
}

.channel-header__unsubscribe:disabled {
  cursor: default;
  opacity: 0.72;
}

.channel-header__spinner {
  width: 0.72rem;
  height: 0.72rem;
  border: 1.5px solid hsl(var(--foreground) / 0.24);
  border-top-color: hsl(var(--foreground));
  border-radius: 9999px;
  animation: channel-header-spin 0.7s linear infinite;
}

.channel-header__error {
  margin-top: 0.4rem;
  font-size: 0.75rem;
  color: hsl(var(--destructive));
}

.channel-dismiss-enter-active,
.channel-dismiss-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease, max-height 0.18s ease, margin 0.18s ease, padding 0.18s ease;
  overflow: hidden;
}

.channel-dismiss-enter-from,
.channel-dismiss-leave-to {
  opacity: 0;
  transform: translateY(-6px);
  max-height: 0;
}

.channel-dismiss-enter-to,
.channel-dismiss-leave-from {
  opacity: 1;
  transform: translateY(0);
  max-height: 12rem;
}

@keyframes channel-header-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (min-width: 640px) {
  .channel-header-content,
  .channel-description {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .channel-header-content,
  .channel-description {
    padding: 0 2rem;
  }
}

@media (max-width: 640px) {
  .channel-header__title {
    width: 100%;
    white-space: normal;
  }

  .channel-header__unsubscribe {
    min-width: 4.8rem;
    min-height: 1.7rem;
    padding: 0 0.64rem;
  }
}
</style>


