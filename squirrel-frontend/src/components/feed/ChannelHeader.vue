<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="channel-terminal-header">
      <div class="header-overlay"></div>
      <div class="header-content">
        <div class="channel-main-info">
          <div class="avatar-frame">
            <img
              v-if="detail"
              :src="getAvatarSrc(detail.avatar, subscriptionId)"
              class="channel-avatar-minimal"
              alt="avatar"
              referrerpolicy="no-referrer"
              @error="(e) => handleAvatarError(e, subscriptionId)"
            />
            <div class="avatar-scan"></div>
          </div>

          <div class="channel-text-minimal">
            <div class="channel-top-row">
              <span class="tech-index">SOURCE_ID // {{ String(subscriptionId).slice(-4).toUpperCase() }}</span>
              <h2 class="channel-title-minimal">{{ detail?.name || 'UNKNOWN_CHANNEL' }}</h2>
              <span v-if="detail?.is_nsfw" class="nsfw-tag">NSFW_RESTRICTED</span>
            </div>

            <div class="channel-stats-minimal">
              <div class="stat-item">
                <span class="stat-label">TOTAL_VIDEOS</span>
                <span class="stat-value">{{ detail?.total_videos || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">EXTRACTED</span>
                <span class="stat-value">{{ detail?.total_extract || 0 }}</span>
              </div>
            </div>
          </div>
        </div>

        <button
          type="button"
          class="unsubscribe-minimal"
          :disabled="isUnsubscribing"
          @click="handleUnsubscribe"
        >
          {{ isUnsubscribing ? 'DISCONNECTING...' : 'TERMINATE_SUBSCRIPTION' }}
        </button>
      </div>

      <div v-if="detail?.description" class="channel-desc-minimal">
        <p>{{ detail.description }}</p>
      </div>
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
.channel-terminal-header {
  position: relative;
  padding: 3rem 2rem 1.5rem 2rem;
  background: transparent;
  overflow: hidden;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.header-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: linear-gradient(to right, rgba(255, 77, 0, 0.02) 0%, transparent 50%);
  pointer-events: none;
}

.header-content {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 2rem;
  z-index: 1;
}

.channel-main-info {
  display: flex;
  gap: 2rem;
  flex: 1;
}

.avatar-frame {
  position: relative;
  width: 80px;
  height: 80px;
  background: #000;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 4px;
}

.channel-avatar-minimal {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: grayscale(0.5);
}

.avatar-scan {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 2px;
  background: #ff4d00;
  opacity: 0.3;
  animation: scan-avatar 3s linear infinite;
}

@keyframes scan-avatar {
  0% { top: 0; }
  100% { top: 100%; }
}

.channel-text-minimal {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.channel-top-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.tech-index {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.6rem;
  color: #ff4d00;
  letter-spacing: 0.2em;
}

.channel-title-minimal {
  font-size: 1.75rem;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.02em;
}

.nsfw-tag {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  color: #ff4d00;
  border: 1px solid #ff4d00;
  padding: 2px 6px;
  width: fit-content;
  margin-top: 0.5rem;
}

.channel-stats-minimal {
  display: flex;
  gap: 2.5rem;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.stat-label {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.5rem;
  color: rgba(255, 255, 255, 0.2);
  letter-spacing: 0.1em;
}

.stat-value {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.6);
}

.unsubscribe-minimal {
  background: transparent;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.4);
  font-size: 0.6rem;
  padding: 0.6rem 1.2rem;
  letter-spacing: 0.15em;
  cursor: pointer;
  transition: all 0.3s;
}

.unsubscribe-minimal:hover {
  border-color: #ff4d00;
  color: #ff4d00;
}

.channel-desc-minimal {
  margin-top: 1.5rem;
  max-width: 600px;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.3);
  line-height: 1.6;
}

.channel-dismiss-enter-active,
.channel-dismiss-leave-active {
  transition: all 0.4s cubic-bezier(0.19, 1, 0.22, 1);
}

.channel-dismiss-enter-from,
.channel-dismiss-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>


