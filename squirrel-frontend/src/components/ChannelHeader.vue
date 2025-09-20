<template>
  <div class="channel-header w-full border-b border-gray-200 dark:border-gray-800">
    <div class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8 py-4 flex items-center justify-between">
      <div class="flex items-center min-w-0">
        <img v-if="detail?.avatar" :src="detail.avatar" class="w-12 h-12 rounded-full object-cover mr-4" alt="avatar" />
        <div class="min-w-0">
          <div class="flex items-center space-x-2">
            <h2 class="text-lg font-semibold truncate">{{ detail?.name || '频道' }}</h2>
            <span v-if="detail?.is_nsfw" class="text-xs px-1.5 py-0.5 rounded bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300">NSFW</span>
          </div>
          <div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5 truncate">
            <span class="mr-3">共 {{ detail?.total_videos || 0 }} 个视频</span>
            <span>已抓取 {{ detail?.total_extract || 0 }}</span>
          </div>
        </div>
      </div>
      <div class="flex items-center space-x-2">
        <button class="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800"
                @click="$emit('refresh')">
          刷新
        </button>
      </div>
    </div>
  </div>
  <div v-if="detail?.description" class="max-w-[1800px] mx-auto w-full px-4 sm:px-6 lg:px-8 pb-3 text-sm text-gray-600 dark:text-gray-300">
    <p class="whitespace-pre-line line-clamp-3">{{ detail.description }}</p>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue';
import { useSubscriptionApi } from '../composables/useSubscriptionApi';

const props = defineProps({
  subscriptionId: { type: [String, Number], required: true }
});

const detail = ref(null);
const loading = ref(false);
const { getSubscriptionDetail } = useSubscriptionApi();

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


