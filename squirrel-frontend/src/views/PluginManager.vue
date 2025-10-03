<template>
  <div class="plugin-manager bg-[#0f0f0f] text-white min-h-screen">
    <!-- 顶部操作区 -->
    <div class="border-b border-white/10">
      <div class="max-w-[1800px] mx-auto px-6 py-6">
        <div class="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div>
            <h1 class="text-xl font-medium mb-1">插件管理</h1>
            <p class="text-sm text-[#aaaaaa]">导入、启用或卸载插件，控制后端扩展能力</p>
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
    <div class="max-w-[1800px] mx-auto px-6 py-6">
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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue';
import { usePluginApi } from '../composables/usePluginApi';

const { getPlugins, installPlugin, enablePlugin, disablePlugin, uninstallPlugin, reloadPlugins } = usePluginApi();

const loading = ref(false);
const installing = ref(false);
const reloading = ref(false);
const plugins = ref([]);
const selectedFile = ref(null);
const actioning = ref(null);

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


