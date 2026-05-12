<template>
  <transition name="channel-dismiss">
    <div v-if="isVisible" class="relative bg-background border-b border-border/40 overflow-hidden">
      <div class="max-w-[2560px] mx-auto px-4 sm:px-6 lg:px-8 py-4 sm:py-6 relative z-10 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        
        <div class="flex items-center gap-4 min-w-0">
          <!-- Avatar -->
          <a
            v-if="detail?.url"
            :href="detail.url"
            target="_blank"
            rel="noopener noreferrer"
            class="shrink-0 h-12 w-12 overflow-hidden rounded-full sm:h-14 sm:w-14"
          >
            <SubscriptionAvatar
              :src="detail?.avatar || null"
              :name="detail?.name || '未知频道'"
              size="full"
            />
          </a>
          <div v-else class="shrink-0 h-12 w-12 overflow-hidden rounded-full sm:h-14 sm:w-14">
            <SubscriptionAvatar
              :src="detail?.avatar || null"
              :name="detail?.name || '未知频道'"
              size="full"
            />
          </div>

          <!-- Info -->
          <div class="flex flex-col gap-1 min-w-0">
            <div class="flex items-center gap-2 min-w-0">
              <a
                v-if="detail?.url"
                :href="detail.url"
                target="_blank"
                rel="noopener noreferrer"
                class="hover:text-primary transition-colors min-w-0"
              >
                <h2 class="text-base sm:text-lg font-bold text-foreground truncate tracking-tight">{{ detail?.name || '未知频道' }}</h2>
              </a>
              <h2 v-else class="text-base sm:text-lg font-bold text-foreground truncate tracking-tight">{{ detail?.name || '未知频道' }}</h2>
              
              <span v-if="detail?.is_nsfw" class="shrink-0 px-1.5 py-0.5 text-[10px] font-bold tracking-widest uppercase border border-primary/50 text-primary rounded-md">NSFW</span>
            </div>
            
            <p v-if="detail?.description" class="text-xs text-muted-foreground/80 line-clamp-1 sm:line-clamp-2 max-w-2xl leading-relaxed">
              {{ detail.description }}
            </p>
          </div>
        </div>

        <!-- Stats & Actions -->
        <div class="flex items-center gap-6 sm:gap-8 shrink-0 ml-[4rem] sm:ml-0">
          <div class="flex items-center gap-4 sm:gap-6">
            <div class="flex flex-col items-center">
              <span class="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-1">总数</span>
              <span class="text-sm font-semibold font-mono text-foreground/80">{{ detail?.total_videos || 0 }}</span>
            </div>
            <div class="flex flex-col items-center">
              <span class="text-[10px] font-bold text-muted-foreground/50 uppercase tracking-widest mb-1">解析</span>
              <span class="text-sm font-semibold font-mono text-foreground/80">{{ detail?.total_extract || 0 }}</span>
            </div>
          </div>
          
          <button
            type="button"
            class="px-3 py-1.5 text-xs font-semibold rounded-md border border-destructive/30 text-destructive hover:bg-destructive/10 transition-colors disabled:opacity-50"
            :disabled="isUnsubscribing"
            @click="handleUnsubscribe"
          >
            {{ isUnsubscribing ? '取消中...' : '取消订阅' }}
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>

<script setup>
import { ref, watch } from 'vue';
import SubscriptionAvatar from '@/components/common/SubscriptionAvatar.vue'
import { getSubscriptionDetail, unsubscribe as apiUnsubscribe } from '@/api'
import { notifySubscriptionRemoved } from '@/utils/subscriptionEvents'

const props = defineProps({
  subscriptionId: { type: [String, Number], required: true }
});

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
  notifySubscriptionRemoved(props.subscriptionId)
  await wait(DISMISS_MS)
}

watch(() => props.subscriptionId, () => {
  isVisible.value = true
  isUnsubscribing.value = false
  unsubscribeError.value = ''
  fetchDetail()
}, { immediate: true });
</script>

<style scoped>
.channel-dismiss-enter-active,
.channel-dismiss-leave-active {
  transition: all var(--duration-slow) var(--ease-out);
}

.channel-dismiss-enter-from,
.channel-dismiss-leave-to {
  opacity: 0;
  transform: translateY(-20px);
}
</style>
