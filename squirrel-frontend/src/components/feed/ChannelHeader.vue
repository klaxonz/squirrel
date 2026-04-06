<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="channel-terminal-header">
      <div class="header-overlay"></div>
      <div class="latest-videos__container channel-header__container">
        <div class="header-content">
          <div class="channel-main-info">
          <div class="avatar-frame">
              <SubscriptionAvatar
                :src="detail?.avatar || null"
                :name="detail?.name || 'UNKNOWN_CHANNEL'"
                size="lg"
                class="channel-avatar-card"
              />
              <div class="avatar-scan"></div>
            </div>

            <div class="channel-text-minimal">
              <div class="channel-top-row">
                <div class="channel-title-row">
                  <h2 class="channel-title-minimal">{{ detail?.name || 'UNKNOWN_CHANNEL' }}</h2>
                  <button
                  type="button"
                  class="unsubscribe-minimal unsubscribe-minimal--tag"
                  :disabled="isUnsubscribing"
                  @click="handleUnsubscribe"
                  >
                    {{ isUnsubscribing ? '取消中...' : '取消订阅' }}
                  </button>
                </div>

                <span v-if="detail?.is_nsfw" class="nsfw-tag nsfw-tag--muted">NSFW</span>
              </div>
            </div>
        </div>

          <div class="channel-side-meta">
            <div class="channel-stats-minimal">
              <div class="stat-item">
                <span class="stat-label">总数</span>
                <span class="stat-value">{{ detail?.total_videos || 0 }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">解析</span>
                <span class="stat-value">{{ detail?.total_extract || 0 }}</span>
              </div>
            </div>
          </div>
        </div>

        <div v-if="detail?.description" class="channel-desc-minimal">
          <p>{{ detail.description }}</p>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useRouter } from 'vue-router'
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
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
  padding: 0;
  background: transparent;
  overflow: hidden;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
}

.channel-header__container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding: 0 1rem;
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
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0 1rem;
}

.channel-main-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex: 1;
  min-width: 0;
}

.avatar-frame {
  position: relative;
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  border-radius: 8px;
  overflow: hidden;
}

.channel-avatar-card {
  display: block;
  width: 100%;
  height: 100%;
}

.channel-avatar-card.avatar--lg {
  width: 100%;
  height: 100%;
}

.channel-avatar-card:deep(.subscription-avatar) {
  border-radius: 8px;
}

.channel-avatar-card:deep(.avatar-image) {
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
  gap: 0.25rem;
  min-width: 0;
  flex: 1;
}

.channel-top-row {
  display: flex;
  flex-direction: column;
  gap: 0.28rem;
  min-width: 0;
}

.channel-title-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  min-width: 0;
}

.channel-side-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-shrink: 0;
}

.channel-title-minimal {
  font-size: 1.15rem;
  line-height: 1.15;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.02em;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.nsfw-tag {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.55rem;
  color: #ff4d00;
  border: 1px solid #ff4d00;
  padding: 2px 6px;
  width: fit-content;
  flex-shrink: 0;
}

.nsfw-tag--muted {
  border: none;
  padding: 0;
  color: rgba(255, 77, 0, 0.7);
}

.channel-stats-minimal {
  display: flex;
  gap: 0.9rem;
  flex-wrap: nowrap;
  justify-content: flex-end;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.7rem;
  white-space: nowrap;
}

.stat-label {
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.58rem;
  line-height: 1;
  color: rgba(255, 255, 255, 0.2);
  letter-spacing: 0.1em;
}

.stat-value {
  font-family: 'Courier New', Courier, monospace;
  font-size: 1.02rem;
  line-height: 1.05;
  color: rgba(255, 255, 255, 0.6);
}

.unsubscribe-minimal {
  background: transparent;
  border: none;
  color: rgba(255, 77, 0, 0.7);
  font-size: 0.54rem;
  padding: 0;
  letter-spacing: 0.1em;
  cursor: pointer;
  transition: all 0.3s;
  white-space: nowrap;
  width: fit-content;
  margin-top: 0.05rem;
  text-align: left;
}

.unsubscribe-minimal--tag {
  border: 1px solid #ff4d00;
  color: #ff4d00;
  padding: 2px 6px;
  margin-top: 0;
}

.unsubscribe-minimal:hover {
  color: #ff4d00;
}

.channel-desc-minimal {
  margin-top: 0.45rem;
  max-width: 600px;
  font-size: 0.66rem;
  color: rgba(255, 255, 255, 0.3);
  line-height: 1.42;
}

.channel-desc-minimal p {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
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

@media (max-width: 900px) {
  .channel-title-minimal {
    font-size: 1.05rem;
  }
}

@media (min-width: 640px) {
  .channel-header__container {
    padding: 0 1.5rem;
  }
}

@media (min-width: 1024px) {
  .channel-header__container {
    padding: 0 2rem;
  }
}

@media (max-width: 640px) {
  .header-content {
    flex-direction: column;
    gap: 0.45rem;
  }

  .channel-main-info {
    width: 100%;
    align-items: flex-start;
  }

  .channel-side-meta {
    width: 100%;
    justify-content: flex-start;
    padding-left: calc(46px + 0.75rem);
  }

  .avatar-frame {
    width: 46px;
    height: 46px;
  }

  .channel-title-row {
    width: 100%;
  }

  .channel-stats-minimal {
    justify-content: flex-start;
  }

  .channel-title-minimal {
    white-space: normal;
  }

  .channel-desc-minimal {
    margin-top: 0.4rem;
    font-size: 0.64rem;
  }
}
</style>


