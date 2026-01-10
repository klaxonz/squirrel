<template>
  <div class="channel-header w-full">
    <div class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8 pt-4">
      <div class="flex items-center justify-between pb-3">
        <div class="flex items-center min-w-0">
          <img v-if="detail" :src="getAvatarSrc(detail.avatar, subscriptionId)" class="w-12 h-12 rounded-full object-cover mr-4" alt="avatar" referrerpolicy="no-referrer" @error="(e) => handleAvatarError(e, subscriptionId)" />
          <div class="min-w-0">
            <div class="flex items-center space-x-2">
              <h2 class="text-lg font-semibold truncate">{{ detail?.name || '频道' }}</h2>
              <span v-if="detail?.is_nsfw" class="text-2xs font-medium px-1.5 py-0.5 rounded bg-color-error/20 text-color-error border border-color-error/30">NSFW</span>
            </div>
            <div class="text-xs text-text-muted mt-0.5 truncate">
              <span class="mr-3">共 {{ detail?.total_videos || 0 }} 个视频</span>
              <span>已抓取 {{ detail?.total_extract || 0 }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <div v-if="detail?.description" class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8 pb-3 text-sm text-text-secondary">
    <p class="whitespace-pre-line line-clamp-3">{{ detail.description }}</p>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue';
import { useSubscriptionApi } from '../composables/useSubscriptionApi';
import { useImageFallback } from '../composables/useImageFallback';

const props = defineProps({
  subscriptionId: { type: [String, Number], required: true }
});

const detail = ref(null);
const loading = ref(false);
const { getSubscriptionDetail } = useSubscriptionApi();
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();

const fetchDetail = async () => {
  if (!props.subscriptionId) return;
  loading.value = true;
  const { success, data } = await getSubscriptionDetail(props.subscriptionId);
  if (success) detail.value = data;
  loading.value = false;
};

watch(() => props.subscriptionId, fetchDetail, { immediate: true });
onMounted(fetchDetail);
</script>

<style scoped>
.channel-header { backdrop-filter: blur(6px); }
</style>


