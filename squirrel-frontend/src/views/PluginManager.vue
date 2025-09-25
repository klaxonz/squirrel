<template>
  <div class="p-6 text-white">
    <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between mb-6">
      <div>
        <h1 class="text-2xl font-semibold">插件管理</h1>
        <p class="text-sm text-[#9ca3af] mt-1">导入、启用或卸载插件，控制后端扩展能力</p>
      </div>
      <div class="flex flex-col sm:flex-row sm:items-center gap-3">
        <div class="flex items-center gap-3 bg-[#1f2937] rounded-lg px-4 py-3 border border-[#374151]">
          <input
            type="file"
            accept=".zip"
            class="text-sm w-40"
            @change="handleFileChange"
          />
          <button
            class="px-4 py-2 bg-[#2563eb] hover:bg-[#1d4ed8] text-white rounded-md text-sm disabled:opacity-60 disabled:cursor-not-allowed"
            :disabled="!selectedFile || installing"
            @click="handleInstall"
          >
            {{ installing ? '安装中...' : '导入插件' }}
          </button>
        </div>
        <button
          class="px-4 py-2 bg-[#374151] hover:bg-[#4b5563] rounded-md text-sm disabled:opacity-60 disabled:cursor-not-allowed"
          :disabled="reloading || loading"
          @click="handleReload"
        >
          {{ reloading ? '重载中...' : '重新加载插件' }}
        </button>
      </div>
    </div>

    <div class="bg-[#111827] border border-[#1f2937] rounded-xl overflow-hidden">
      <div class="border-b border-[#1f2937] px-6 py-3 flex items-center justify-between text-xs uppercase tracking-wide text-[#9ca3af]">
        <span>插件列表</span>
        <span v-if="loading" class="animate-pulse">加载中...</span>
      </div>

      <div v-if="!loading && plugins.length === 0" class="p-10 text-center text-[#9ca3af]">
        暂无插件，请先导入 zip 包后再启用。
      </div>

      <div v-else class="overflow-x-auto">
        <table class="min-w-full text-sm">
          <thead class="bg-[#1f2937] text-left text-[#9ca3af]">
            <tr>
              <th class="px-6 py-3 font-medium">名称</th>
              <th class="px-6 py-3 font-medium">版本</th>
              <th class="px-6 py-3 font-medium">来源</th>
              <th class="px-6 py-3 font-medium hidden lg:table-cell">描述</th>
              <th class="px-6 py-3 font-medium text-center">状态</th>
              <th class="px-6 py-3 font-medium text-right">操作</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="plugin in plugins"
              :key="plugin.name"
              class="border-t border-[#1f2937] hover:bg-[#1f2937]/60 transition"
            >
              <td class="px-6 py-4">
                <div class="flex items-center gap-2">
                  <span class="font-medium text-white">{{ plugin.name }}</span>
                  <span
                    v-if="plugin.state === 'missing'"
                    class="px-2 py-[2px] text-[11px] rounded-full bg-red-500/20 text-red-300"
                  >
                    配置缺失
                  </span>
                  <span
                    v-else-if="plugin.source === 'external'"
                    class="px-2 py-[2px] text-[11px] rounded-full bg-emerald-500/20 text-emerald-300"
                  >
                    外部
                  </span>
                  <span
                    v-else-if="plugin.source === 'internal'"
                    class="px-2 py-[2px] text-[11px] rounded-full bg-sky-500/20 text-sky-300"
                  >
                    内置
                  </span>
                  <span
                    v-else-if="plugin.source === 'package'"
                    class="px-2 py-[2px] text-[11px] rounded-full bg-purple-500/20 text-purple-300"
                  >
                    包安装
                  </span>
                </div>
                <div v-if="plugin.module" class="text-xs text-[#6b7280] mt-1">{{ plugin.module }}</div>
              </td>
              <td class="px-6 py-4 text-[#d1d5db]">{{ plugin.version || '—' }}</td>
              <td class="px-6 py-4 text-[#d1d5db]">{{ formatSource(plugin.source) }}</td>
              <td class="px-6 py-4 hidden lg:table-cell text-[#9ca3af] max-w-xs">
                <div class="line-clamp-2">{{ plugin.description || '暂无描述' }}</div>
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center justify-center">
                  <span
                    class="px-3 py-1 rounded-full text-xs"
                    :class="plugin.enabled ? 'bg-green-500/20 text-green-300' : 'bg-[#4b5563] text-[#d1d5db]'"
                  >
                    {{ plugin.enabled ? '已启用' : '已禁用' }}
                  </span>
                </div>
              </td>
              <td class="px-6 py-4">
                <div class="flex items-center gap-2 justify-end">
                  <button
                    class="px-3 py-1.5 rounded-md text-xs bg-[#2563eb] hover:bg-[#1d4ed8] disabled:opacity-60 disabled:cursor-not-allowed"
                    :disabled="actioning === plugin.name || plugin.state === 'missing' || plugin.enabled"
                    @click="handleEnable(plugin)"
                  >
                    启用
                  </button>
                  <button
                    class="px-3 py-1.5 rounded-md text-xs bg-[#374151] hover:bg-[#4b5563] disabled:opacity-60 disabled:cursor-not-allowed"
                    :disabled="actioning === plugin.name || plugin.state === 'missing' || !plugin.enabled"
                    @click="handleDisable(plugin)"
                  >
                    禁用
                  </button>
                  <button
                    v-if="plugin.source === 'external'"
                    class="px-3 py-1.5 rounded-md text-xs bg-[#b91c1c] hover:bg-[#dc2626] disabled:opacity-60 disabled:cursor-not-allowed"
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
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>


