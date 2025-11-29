<template>
  <div class="plugin-manager bg-[#0f0f0f] text-white min-h-screen">
    <!-- 顶部操作区 -->
    <div class="border-b border-white/10">
      <div class="max-w-[1800px] mx-auto px-6 py-6">
        <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div>
            <h1 class="text-xl font-medium mb-1">插件管理</h1>
            <p class="text-sm text-[#aaaaaa]">导入、启用或卸载插件，控制后端扩展能力</p>
            
            <!-- 标签页切换 -->
            <div class="flex gap-1 mt-4">
              <button
                @click="currentTab = 'plugins'"
                class="px-4 py-2 text-sm font-medium rounded-full transition-colors"
                :class="currentTab === 'plugins' ? 'bg-white/10 text-white' : 'text-[#aaaaaa] hover:text-white hover:bg-white/5'"
              >
                插件列表
              </button>
              <button
                @click="currentTab = 'connectivity'"
                class="px-4 py-2 text-sm font-medium rounded-full transition-colors"
                :class="currentTab === 'connectivity' ? 'bg-white/10 text-white' : 'text-[#aaaaaa] hover:text-white hover:bg-white/5'"
              >
                站点连通性
              </button>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <label class="flex items-center gap-3 px-4 py-2 bg-white/5 hover:bg-white/10 rounded-full cursor-pointer transition-colors">
              <input
                type="file"
                accept=".zip"
                class="hidden"
                @change="handleFileChange"
              />
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
              </svg>
              <span class="text-sm font-medium">{{ selectedFile ? selectedFile.name : '选择文件' }}</span>
            </label>
            <button
              class="px-4 py-2 bg-[#cc0000] hover:bg-[#ff0000] rounded-full text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              :disabled="!selectedFile || installing"
              @click="handleInstall"
            >
              {{ installing ? '安装中...' : '导入插件' }}
            </button>
            <button
              class="p-2 hover:bg-white/10 rounded-full transition-colors disabled:opacity-40"
              :disabled="reloading || loading"
              @click="handleReload"
              title="重新加载插件"
            >
              <svg class="w-5 h-5" :class="{ 'animate-spin': reloading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 插件列表 -->
    <div v-if="currentTab === 'plugins'" class="max-w-[1800px] mx-auto px-6 py-6">
      <div v-if="loading" class="flex items-center justify-center py-20">
        <div class="animate-spin rounded-full h-8 w-8 border-2 border-white/20 border-t-white"></div>
      </div>

      <div v-else-if="plugins.length === 0" class="flex flex-col items-center justify-center py-20 text-[#aaaaaa]">
        <svg class="w-16 h-16 mb-4 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
        </svg>
        <p class="text-sm">暂无插件</p>
        <p class="text-xs mt-1">请导入插件 ZIP 包</p>
      </div>

      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-white/10">
              <th class="text-left py-3 px-4 text-sm font-medium text-[#aaaaaa]">名称</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-[#aaaaaa]">版本</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-[#aaaaaa]">来源</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-[#aaaaaa] hidden lg:table-cell">描述</th>
              <th class="text-center py-3 px-4 text-sm font-medium text-[#aaaaaa]">状态</th>
              <th class="text-right py-3 px-4 text-sm font-medium text-[#aaaaaa]">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="plugin in plugins"
              :key="plugin.name"
              class="border-b border-white/5 hover:bg-white/5 transition-colors"
            >
              <td class="py-4 px-4">
                <div>
                  <div class="flex items-center gap-2">
                    <span class="font-medium">{{ plugin.name }}</span>
                    <span
                      v-if="plugin.state === 'missing'"
                      class="px-2 py-0.5 text-[10px] rounded bg-red-500/20 text-red-400 font-medium"
                    >
                      配置缺失
                    </span>
                    <span
                      v-else-if="plugin.source === 'external'"
                      class="px-2 py-0.5 text-[10px] rounded bg-blue-500/20 text-blue-400 font-medium"
                    >
                      外部
                    </span>
                    <span
                      v-else-if="plugin.source === 'internal'"
                      class="px-2 py-0.5 text-[10px] rounded bg-purple-500/20 text-purple-400 font-medium"
                    >
                      内置
                    </span>
                  </div>
                  <div v-if="plugin.module" class="text-xs text-[#aaaaaa] mt-0.5">{{ plugin.module }}</div>
                </div>
              </td>
              <td class="py-4 px-4 text-[#aaaaaa] text-sm">{{ plugin.version || '—' }}</td>
              <td class="py-4 px-4 text-[#aaaaaa] text-sm">{{ formatSource(plugin.source) }}</td>
              <td class="py-4 px-4 text-[#aaaaaa] text-sm hidden lg:table-cell max-w-md">
                <div class="line-clamp-2">{{ plugin.description || '暂无描述' }}</div>
              </td>
              <td class="py-4 px-4">
                <div class="flex justify-center">
                  <span
                    class="px-2.5 py-1 rounded text-xs font-medium"
                    :class="plugin.enabled ? 'bg-green-500/20 text-green-400' : 'bg-white/5 text-[#aaaaaa]'"
                  >
                    {{ plugin.enabled ? '已启用' : '已禁用' }}
                  </span>
                </div>
              </td>
              <td class="py-4 px-4">
                <div class="flex items-center justify-end gap-2">
                  <button
                    v-if="!plugin.enabled"
                    class="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    :disabled="actioning === plugin.name || plugin.state === 'missing'"
                    @click="handleEnable(plugin)"
                  >
                    启用
                  </button>
                  <button
                    v-if="plugin.enabled"
                    class="px-3 py-1.5 bg-white/5 hover:bg-white/10 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    :disabled="actioning === plugin.name || plugin.state === 'missing'"
                    @click="handleDisable(plugin)"
                  >
                    禁用
                  </button>
                  <button
                    v-if="plugin.source === 'external'"
                    class="px-3 py-1.5 bg-white/5 hover:bg-red-600/20 hover:text-red-400 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                    :disabled="actioning === plugin.name"
                    @click="handleUninstall(plugin)"
                  >
                    卸载
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 站点连通性测试 -->
    <div v-if="currentTab === 'connectivity'" class="max-w-[1800px] mx-auto px-6 py-6">
      <!-- 操作区 -->
      <div class="flex items-center justify-between mb-6">
        <div class="text-sm text-[#aaaaaa]">
          共 {{ siteStats.total }} 个支持的站点
        </div>
        <div class="flex items-center gap-3">
          <button
            @click="handleTestAll"
            :disabled="testingAll || loadingSites"
            class="px-4 py-2 bg-[#cc0000] hover:bg-[#ff0000] rounded-full text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
          >
            <svg v-if="testingAll" class="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            {{ testingAll ? '测试中...' : '测试全部' }}
          </button>
        </div>
      </div>

      <!-- 统计信息 -->
      <div v-if="connectivityResults.length > 0" class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div class="bg-white/5 rounded-lg p-4">
          <div class="text-[#aaaaaa] text-xs mb-1">总站点数</div>
          <div class="text-2xl font-medium">{{ connectivitySummary.total }}</div>
        </div>
        <div class="bg-green-500/10 rounded-lg p-4">
          <div class="text-green-400 text-xs mb-1">可访问</div>
          <div class="text-2xl font-medium text-green-400">{{ connectivitySummary.accessible }}</div>
        </div>
        <div class="bg-red-500/10 rounded-lg p-4">
          <div class="text-red-400 text-xs mb-1">不可访问</div>
          <div class="text-2xl font-medium text-red-400">{{ connectivitySummary.failed }}</div>
        </div>
        <div class="bg-blue-500/10 rounded-lg p-4">
          <div class="text-blue-400 text-xs mb-1">成功率</div>
          <div class="text-2xl font-medium text-blue-400">{{ connectivitySummary.success_rate }}%</div>
        </div>
      </div>

      <!-- 加载状态 -->
      <div v-if="loadingSites" class="flex items-center justify-center py-20">
        <div class="animate-spin rounded-full h-8 w-8 border-2 border-white/20 border-t-white"></div>
      </div>

      <!-- 站点列表 -->
      <div v-else class="overflow-x-auto">
        <table class="w-full">
          <thead>
            <tr class="border-b border-white/10">
              <th class="text-left py-3 px-4 text-sm font-medium text-[#aaaaaa]">站点名称</th>
              <th class="text-left py-3 px-4 text-sm font-medium text-[#aaaaaa] hidden lg:table-cell">支持域名</th>
              <th class="text-center py-3 px-4 text-sm font-medium text-[#aaaaaa]">状态</th>
              <th class="text-center py-3 px-4 text-sm font-medium text-[#aaaaaa]">响应时间</th>
              <th class="text-center py-3 px-4 text-sm font-medium text-[#aaaaaa] hidden md:table-cell">IP地址</th>
              <th class="text-right py-3 px-4 text-sm font-medium text-[#aaaaaa]">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="site in displaySites"
              :key="site.site_name"
              class="border-b border-white/5 hover:bg-white/5 transition-colors"
            >
              <td class="py-4 px-4">
                <div class="font-medium">{{ site.site_name || site.name }}</div>
                <div v-if="site.test_url" class="text-xs text-[#aaaaaa] mt-0.5">{{ site.test_url }}</div>
              </td>
              <td class="py-4 px-4 hidden lg:table-cell">
                <div class="flex flex-wrap gap-1">
                  <span
                    v-for="domain in site.domains?.slice(0, 3) || []"
                    :key="domain"
                    class="px-2 py-0.5 text-[10px] rounded bg-white/5 text-[#aaaaaa]"
                  >
                    {{ domain }}
                  </span>
                  <span
                    v-if="site.domains?.length > 3"
                    class="px-2 py-0.5 text-[10px] rounded bg-white/5 text-[#aaaaaa]"
                  >
                    +{{ site.domains.length - 3 }}
                  </span>
                </div>
              </td>
              <td class="py-4 px-4">
                <div class="flex justify-center">
                  <span
                    v-if="site.testing"
                    class="px-2.5 py-1 rounded text-xs font-medium bg-blue-500/20 text-blue-400 flex items-center gap-1"
                  >
                    <svg class="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    测试中
                  </span>
                  <span
                    v-else-if="site.accessible === true"
                    class="px-2.5 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400"
                  >
                    ✓ 可访问
                  </span>
                  <span
                    v-else-if="site.accessible === false"
                    class="px-2.5 py-1 rounded text-xs font-medium bg-red-500/20 text-red-400"
                    :title="site.error_message"
                  >
                    ✗ 不可访问
                  </span>
                  <span
                    v-else
                    class="px-2.5 py-1 rounded text-xs font-medium bg-white/5 text-[#aaaaaa]"
                  >
                    未测试
                  </span>
                </div>
              </td>
              <td class="py-4 px-4 text-center text-sm text-[#aaaaaa]">
                {{ site.response_time ? `${site.response_time}ms` : '—' }}
              </td>
              <td class="py-4 px-4 text-center text-sm text-[#aaaaaa] hidden md:table-cell">
                {{ site.ip_address || '—' }}
              </td>
              <td class="py-4 px-4">
                <div class="flex items-center justify-end gap-2">
                  <button
                    @click="handleTestSingle(site)"
                    :disabled="site.testing || testingAll"
                    class="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {{ site.testing ? '测试中...' : '测试' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch } from 'vue';
import { usePluginApi } from '../composables/usePluginApi';

const { 
  getPlugins, 
  installPlugin, 
  enablePlugin, 
  disablePlugin, 
  uninstallPlugin, 
  reloadPlugins,
  getSupportedSites,
  testSiteConnectivity,
  testAllSitesConnectivity
} = usePluginApi();

// 插件管理相关状态
const currentTab = ref('plugins');
const loading = ref(false);
const installing = ref(false);
const reloading = ref(false);
const plugins = ref([]);
const selectedFile = ref(null);
const actioning = ref(null);

// 站点连通性测试相关状态
const loadingSites = ref(false);
const testingAll = ref(false);
const supportedSites = ref([]);
const connectivityResults = ref([]);

// 计算属性
const siteStats = computed(() => ({
  total: supportedSites.value.length || 0
}));

const connectivitySummary = computed(() => {
  if (connectivityResults.value.length === 0) {
    return { total: 0, accessible: 0, failed: 0, success_rate: 0 };
  }
  return connectivityResults.value[0]?.summary || { total: 0, accessible: 0, failed: 0, success_rate: 0 };
});

const displaySites = computed(() => {
  // 合并支持的站点列表和测试结果
  const resultsMap = new Map();
  if (connectivityResults.value.length > 0 && connectivityResults.value[0]?.results) {
    connectivityResults.value[0].results.forEach(result => {
      resultsMap.set(result.site_name, result);
    });
  }

  return supportedSites.value.map(siteInfo => {
    const siteName = siteInfo.name;
    const result = resultsMap.get(siteName);
    
    // 合并站点信息和测试结果
    return {
      ...siteInfo,
      ...result,
      site_name: siteName,
      // 优先使用测试结果中的域名和test_url，否则使用站点基本信息
      domains: result?.domains || siteInfo.domains || [],
      test_url: result?.test_url || siteInfo.test_url || ''
    };
  });
});

const fetchPlugins = async () => {
  loading.value = true;
  const result = await getPlugins();
  if (result.success) {
    plugins.value = result.data;
  }
  loading.value = false;
};

const handleFileChange = (event) => {
  const [file] = event.target.files || [];
  selectedFile.value = file || null;
};

const handleInstall = async () => {
  if (!selectedFile.value) return;
  installing.value = true;
  const res = await installPlugin(selectedFile.value);
  if (res.success) {
    selectedFile.value = null;
    await fetchPlugins();
  }
  installing.value = false;
};

const handleReload = async () => {
  reloading.value = true;
  const res = await reloadPlugins();
  if (res.success) {
    await fetchPlugins();
  }
  reloading.value = false;
};

const handleEnable = async (plugin) => {
  actioning.value = plugin.name;
  const res = await enablePlugin(plugin.name);
  if (res.success) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const handleDisable = async (plugin) => {
  actioning.value = plugin.name;
  const res = await disablePlugin(plugin.name);
  if (res.success) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const handleUninstall = async (plugin) => {
  actioning.value = plugin.name;
  const res = await uninstallPlugin(plugin.name);
  if (res.success) {
    await fetchPlugins();
  }
  actioning.value = null;
};

const formatSource = (source) => {
  switch (source) {
    case 'external':
      return '外部目录';
    case 'internal':
      return '内置插件';
    case 'package':
      return '环境安装';
    case 'missing':
      return '配置缺失';
    default:
      return '未知';
  }
};

// 获取支持的站点列表
const fetchSupportedSites = async () => {
  loadingSites.value = true;
  const result = await getSupportedSites();
  if (result.success && result.data) {
    // 新的API返回结构：{ sites: [{name, domains, primary_domain}], total }
    supportedSites.value = result.data.sites || [];
  }
  loadingSites.value = false;
};

// 测试单个站点
const handleTestSingle = async (site) => {
  const siteName = site.site_name || site.name;
  
  // 设置测试状态
  const index = displaySites.value.findIndex(s => (s.site_name || s.name) === siteName);
  if (index !== -1) {
    displaySites.value[index].testing = true;
  }

  const result = await testSiteConnectivity(siteName);
  
  if (result.success && result.data) {
    // 更新单个站点的测试结果
    if (connectivityResults.value.length === 0) {
      connectivityResults.value = [{ results: [], summary: { total: 0, accessible: 0, failed: 0, success_rate: 0 } }];
    }
    
    const results = connectivityResults.value[0].results;
    const existingIndex = results.findIndex(r => r.site_name === siteName);
    
    if (existingIndex !== -1) {
      results[existingIndex] = result.data;
    } else {
      results.push(result.data);
    }

    // 重新计算统计信息
    const accessible = results.filter(r => r.accessible).length;
    const failed = results.filter(r => !r.accessible).length;
    connectivityResults.value[0].summary = {
      total: results.length,
      accessible,
      failed,
      success_rate: results.length > 0 ? Math.round((accessible / results.length) * 100 * 100) / 100 : 0
    };
  }

  // 清除测试状态
  if (index !== -1) {
    displaySites.value[index].testing = false;
  }
};

// 测试全部站点
const handleTestAll = async () => {
  testingAll.value = true;
  const result = await testAllSitesConnectivity();
  
  if (result.success && result.data) {
    connectivityResults.value = [result.data];
  }
  
  testingAll.value = false;
};

// 监听标签页切换
watch(currentTab, async (newTab) => {
  if (newTab === 'connectivity' && supportedSites.value.length === 0) {
    await fetchSupportedSites();
  }
});

onMounted(() => {
  fetchPlugins();
});
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>


