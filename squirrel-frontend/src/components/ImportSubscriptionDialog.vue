<template>
  <div v-if="show" class="fixed inset-0 bg-black/75 flex items-center justify-center z-50 p-4"
       @click.self="handleClose">
    <div class="bg-bg-card border border-border-primary rounded-lg w-full max-w-3xl max-h-[90vh] flex flex-col">
      <!-- 头部 -->
      <div class="flex items-center justify-between p-6 border-b border-border-primary">
        <h2 class="text-xl font-bold text-text-primary">导入订阅</h2>
        <IconButton title="关闭" aria-label="关闭" @click="handleClose">
          <XMarkIcon class="h-6 w-6" />
        </IconButton>
      </div>

      <!-- 内容区域 -->
      <div class="flex-1 overflow-y-auto p-6">
        <!-- 步骤 1: 选择站点 -->
        <div v-if="step === 1">
          <p class="text-text-muted mb-6">选择要导入的站点，系统将获取您在该站点的订阅列表</p>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <button
              v-for="site in supportedSites"
              :key="site"
              :class="[
                'flex flex-col items-center p-6 rounded-lg border-2 transition-all',
                selectedSite === site
                  ? 'border-color-error bg-color-error/10'
                  : 'border-border-secondary bg-bg-secondary hover:border-border-secondary'      
              ]"
              @click="selectedSite = site"
            >
              <div class="w-12 h-12 mb-3 flex items-center justify-center bg-bg-elevated rounded-lg text-2xl font-bold text-text-primary">
                {{ site.charAt(0).toUpperCase() }}
              </div>
              <span class="text-text-primary font-medium">{{ getSiteName(site) }}</span>
            </button>
          </div>
        </div>

        <!-- 步骤 2: 预览订阅 -->
        <div v-else-if="step === 2">
          <div class="mb-4">
            <p class="text-text-primary font-medium mb-2">预览订阅列表</p>
            <p class="text-text-muted text-sm">
              总计 <span class="text-text-primary font-bold">{{ previewData.total }}</span>，
              已导入 <span class="text-text-primary font-bold">{{ previewData.imported ?? 0 }}</span>，
              未导入 <span class="text-text-primary font-bold">{{ previewData.not_imported ?? 0 }}</span>，
              已选 <span class="text-text-primary font-bold">{{ selectedCount }}</span>
            </p>
          </div>

          <div v-if="loadingPreview" class="flex items-center justify-center py-12">
            <div class="flex space-x-2">
              <div class="w-3 h-3 bg-color-error rounded-full animate-bounce"></div>
              <div class="w-3 h-3 bg-color-error rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
              <div class="w-3 h-3 bg-color-error rounded-full animate-bounce" style="animation-delay: 0.4s"></div>
            </div>
          </div>

          <div v-else>
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <Button size="sm" variant="secondary" shape="pill" @click="selectAllNotImported">全选未导入</Button>
                <Button size="sm" variant="secondary" shape="pill" @click="clearSelection">清空</Button>
              </div>
              <p class="text-text-muted text-sm">
                已选 <span class="text-text-primary font-bold">{{ selectedCount }}</span>
              </p>
            </div>

            <div class="space-y-1 max-h-[400px] overflow-y-auto">
              <div
                v-for="sub in previewData.subscriptions"
                :key="sub.url"
                class="p-3 bg-bg-secondary border border-border-primary rounded-lg hover:bg-bg-tertiary transition-colors flex items-center gap-3"
              >
                <input
                  type="checkbox"
                  class="w-4 h-4 accent-color-error"
                  :disabled="sub.is_imported"
                  :checked="!!selectedUrlMap[sub.url]"
                  @change="toggleSelection(sub)"
                />

                <img
                  :src="getAvatarSrc(sub.avatar, sub.url)"
                  class="w-8 h-8 rounded-full object-cover"
                  alt="avatar"
                  referrerpolicy="no-referrer"
                  @error="(e) => handleAvatarError(e, sub.url)"
                />

                <div class="flex-1 min-w-0">
                  <p class="text-text-primary text-sm truncate">{{ sub.name || '未命名订阅' }}</p>
                  <p class="text-text-tertiary text-xs truncate">{{ sub.url }}</p>     
                </div>

                <span
                  v-if="sub.is_imported"
                  class="text-xs px-2 py-0.5 rounded bg-color-success/20 text-color-success border border-color-success/30"
                >
                  已导入
                </span>
                <span
                  v-else
                  class="text-xs px-2 py-0.5 rounded bg-bg-elevated text-text-muted border border-border-secondary"
                >
                  未导入
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- 步骤 3: 导入结果 -->
        <div v-else-if="step === 3">
          <div class="text-center py-8">
            <div class="flex justify-center mb-4">
              <div class="w-16 h-16 bg-color-success/20 rounded-full flex items-center justify-center">
                <CheckIcon class="w-10 h-10 text-color-success" />
              </div>
            </div>

            <h3 class="text-2xl font-bold text-text-primary mb-6">
              {{ importResult.total > 0 ? '任务已提交' : '没有需要导入的订阅' }}
            </h3>

            <div class="bg-bg-secondary border border-border-primary rounded-lg p-6 mb-6">
              <p class="text-text-muted text-sm mb-2">新增导入任务</p>
              <p class="text-text-primary text-4xl font-bold">{{ importResult.total }}</p>
              <p class="text-text-muted text-xs mt-3">
                拉取 {{ importResult.found ?? 0 }} 个，选择 {{ importResult.selected ?? 0 }} 个，跳过 {{ importResult.skipped ?? 0 }} 个
              </p>
            </div>

            <div class="text-text-muted text-sm bg-bg-secondary border border-border-primary rounded-lg p-4">       
              <ExclamationTriangleIcon class="w-5 h-5 inline-block mr-2" />
              <span v-if="importResult.total > 0">
                导入任务已提交，正在后台处理 {{ importResult.total }} 个订阅。<br>
                处理完成后订阅列表会自动更新，请稍后刷新查看。
              </span>
              <span v-else>
                当前没有需要导入的订阅（可能都已导入或你未选择任何未导入项）。
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部操作按钮 -->
      <div class="flex justify-end gap-3 p-6 border-t border-border-primary">        
        <Button v-if="step === 1" size="md" variant="secondary" :disabled="loadingPreview" @click="handleClose">取消</Button>
        <Button v-if="step === 1" size="md" variant="danger" :disabled="!selectedSite || loadingPreview" :loading="loadingPreview" @click="handlePreview">预览订阅</Button>

        <Button v-if="step === 2" size="md" variant="secondary" :disabled="importing" @click="step = 1">返回</Button>
        <Button
          v-if="step === 2"
          size="md"
          variant="danger"
          :disabled="importing || selectedCount === 0"
          :loading="importing"
          @click="handleImport"
        >
          {{ importing ? '导入中...' : `确认导入 (${selectedCount})` }}
        </Button>

        <Button v-if="step === 3" size="md" variant="danger" @click="handleClose">完成</Button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue';
import {
  XMarkIcon,
  CheckIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon
} from '@heroicons/vue/24/outline';
import IconButton from './common/IconButton.vue';
import Button from './common/Button.vue';
import { useSubscriptionApi } from '../composables/useSubscriptionApi';
import { useImageFallback } from '../composables/useImageFallback';

const props = defineProps({
  show: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['close', 'imported']);
const { getImageSrc: getAvatarSrc, handleImageError: handleAvatarError } = useImageFallback();

const step = ref(1); // 1: 选择站点, 2: 预览, 3: 结果
const supportedSites = ref([]);
const selectedSite = ref('');
const previewData = ref({ total: 0, subscriptions: [] });
const selectedUrlMap = ref({});
const importResult = ref({});
const loadingPreview = ref(false);
const importing = ref(false);

const {
  getSupportedImportSites,
  previewImportSubscriptions,
  importSubscriptions
} = useSubscriptionApi();

// 站点配置
const siteConfig = {
  bilibili: { name: 'Bilibili' },
  youtube: { name: 'YouTube' },
  pornhub: { name: 'Pornhub' },
  javdb: { name: 'JavDB' }
};

const getSiteName = (site) => siteConfig[site]?.name || site.charAt(0).toUpperCase() + site.slice(1);

const selectedCount = computed(() => Object.keys(selectedUrlMap.value || {}).length);

const selectAllNotImported = () => {
  const map = {};
  for (const sub of previewData.value.subscriptions || []) {
    if (sub?.url && !sub.is_imported) {
      map[sub.url] = true;
    }
  }
  selectedUrlMap.value = map;
};

const clearSelection = () => {
  selectedUrlMap.value = {};
};

const toggleSelection = (sub) => {
  if (!sub?.url || sub.is_imported) return;
  const map = { ...(selectedUrlMap.value || {}) };
  if (map[sub.url]) {
    delete map[sub.url];
  } else {
    map[sub.url] = true;
  }
  selectedUrlMap.value = map;
};

// 加载支持的站点
const loadSupportedSites = async () => {
  const result = await getSupportedImportSites();
  if (result.success) {
    supportedSites.value = result.data;
  }
};

// 预览订阅
const handlePreview = async () => {
  if (!selectedSite.value) return;

  loadingPreview.value = true;
  const result = await previewImportSubscriptions(selectedSite.value);
  loadingPreview.value = false;

  if (result.success) {
    previewData.value = result.data;
    selectAllNotImported();
    step.value = 2;
  }
};

// 执行导入
const handleImport = async () => {
  if (!selectedSite.value) return;

  const subscriptionUrls = Object.keys(selectedUrlMap.value || {});
  importing.value = true;
  const result = await importSubscriptions(selectedSite.value, subscriptionUrls);
  importing.value = false;

  if (result.success) {
    importResult.value = result.data;
    step.value = 3;
  }
};

// 关闭对话框
const handleClose = () => {
  emit('close');
  if (step.value === 3 && importResult.value.total > 0) {
    emit('imported');
  }
  // 重置状态
  setTimeout(() => {
    step.value = 1;
    selectedSite.value = '';
    previewData.value = { total: 0, subscriptions: [] };
    selectedUrlMap.value = {};
    importResult.value = {};
  }, 300);
};

// 监听对话框显示状态
watch(() => props.show, (newVal) => {
  if (newVal) {
    loadSupportedSites();
  }
});
</script>

<style scoped>
/* 自定义滚动条 */
::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

::-webkit-scrollbar-track {
  background: #181818;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb {
  background: #404040;
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: #505050;
}
</style>
