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
              <th class="text-center py-3 px-4 text-sm font-medium text-[#aaaaaa]">登录状态</th>
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
                <div class="font-medium flex items-center gap-2">
                  <span>{{ site.display_label || site.site_name || site.name }}</span>
                  <span
                    v-if="site.config_enabled === false"
                    class="px-2 py-0.5 text-[10px] rounded-full bg-red-500/10 text-red-400 border border-red-500/30"
                  >
                    已禁用
                  </span>
                </div>
                <div class="text-xs text-[#aaaaaa] mt-0.5">
                  标识：{{ site.site_name || site.name }}
                </div>
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
              <td class="py-4 px-4">
                <div class="flex justify-center">
                  <span
                    v-if="!site.supports_login_status"
                    class="px-2.5 py-1 rounded text-xs font-medium bg-white/5 text-[#aaaaaa]"
                  >
                    未接入
                  </span>
                  <span
                    v-else-if="site.loginTesting"
                    class="px-2.5 py-1 rounded text-xs font-medium bg-blue-500/20 text-blue-400 flex items-center gap-1"
                  >
                    <svg class="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    检测中
                  </span>
                  <span
                    v-else-if="site.loginStatus?.logged_in"
                    class="px-2.5 py-1 rounded text-xs font-medium bg-green-500/20 text-green-400"
                    :title="site.loginStatus?.message || '已登录'"
                  >
                    已登录
                  </span>
                  <span
                    v-else-if="site.loginStatus"
                    class="px-2.5 py-1 rounded text-xs font-medium bg-red-500/20 text-red-400"
                    :title="site.loginStatus?.message || '未登录'"
                  >
                    未登录
                  </span>
                  <span
                    v-else
                    class="px-2.5 py-1 rounded text-xs font-medium bg-white/5 text-[#aaaaaa]"
                  >
                    未检测
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
                    @click="openSiteEditor(site)"
                    :disabled="!siteCatalogLoaded || siteCatalogLoading"
                    class="px-3 py-1.5 bg-white/20 hover:bg-white/30 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    站点配置
                  </button>
                  <button
                    @click="handleTestSingle(site)"
                    :disabled="site.testing || testingAll"
                    class="px-3 py-1.5 bg-white/10 hover:bg-white/20 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {{ site.testing ? '测试中...' : '连通性' }}
                  </button>
                  <button
                    v-if="site.supports_login_status"
                    @click="handleTestLogin(site)"
                    :disabled="site.loginTesting || testingAll"
                    class="px-3 py-1.5 bg-white/5 hover:bg-white/15 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {{ site.loginTesting ? '检测中...' : '登录检测' }}
                  </button>
                  <button
                    @click="handleUploadCookies(site)"
                    :disabled="site.cookieUploading || testingAll"
                    class="px-3 py-1.5 bg-white/5 hover:bg-white/20 rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    {{ site.cookieUploading ? '上传中...' : '上传Cookie' }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
    </div>
  </div>

    <!-- 站点配置编辑弹窗 -->
    <div
      v-if="siteEditorVisible"
      class="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
    >
      <div class="bg-[#161616] rounded-2xl border border-white/10 w-full max-w-3xl shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-white/10">
          <div>
            <h3 class="text-lg font-semibold">编辑站点配置</h3>
            <p class="text-xs text-[#aaaaaa] mt-1">插件站点：{{ siteEditorForm.siteName }}</p>
          </div>
          <button
            class="text-[#aaaaaa] hover:text-white transition-colors"
            @click="closeSiteEditor"
          >
            ✕
          </button>
        </div>

        <div class="site-editor-scroll px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto pr-2">
          <div>
            <label class="block text-sm text-[#aaaaaa] mb-1">显示名称</label>
            <input
              v-model="siteEditorForm.label"
              class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]"
              placeholder="展示给用户的名称"
            >
          </div>

  <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-[#aaaaaa] mb-1">域名列表</label>
              <textarea
                v-model="siteEditorForm.domainsText"
                rows="5"
                class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]"
                placeholder="每行一个域名，例如：www.youtube.com"
              ></textarea>
              <p class="text-xs text-[#777] mt-1">用于匹配订阅与视频来源，至少填写一个域名。</p>
            </div>
            <div>
              <label class="block text-sm text-[#aaaaaa] mb-1">别名（可选）</label>
              <textarea
                v-model="siteEditorForm.aliasesText"
                rows="5"
                class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]"
                placeholder="每行一个别名，例如：yt、油管"
              ></textarea>
              <p class="text-xs text-[#777] mt-1">别名可用于筛选条件。</p>
            </div>
          </div>

          <div class="flex items-center gap-3 text-sm text-[#aaaaaa]">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="siteEditorForm.enabled" class="accent-[#cc0000]">
              启用该站点（用于筛选/数据爬取）
            </label>
          </div>

          <div>
            <label class="block text-sm text-[#aaaaaa] mb-1">测试 URL</label>
            <input
              v-model="siteEditorForm.testUrl"
              class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]"
              placeholder="用于连通性检测的 URL"
            >
          </div>

          <div>
            <label class="block text-sm text-[#aaaaaa] mb-1">HTTP 请求头（每行 key: value）</label>
            <textarea
              v-model="siteEditorForm.httpHeadersText"
              rows="4"
              class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]"
              placeholder="User-Agent: Mozilla/5.0"
            ></textarea>
          </div>

          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-[#aaaaaa] mb-1">最小请求间隔（秒）</label>
              <input
                type="number"
                step="0.1"
                v-model="siteEditorForm.rateLimitMin"
                class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]"
              >
            </div>
            <div>
              <label class="block text-sm text-[#aaaaaa] mb-1">最大请求间隔（秒）</label>
              <input
                type="number"
                step="0.1"
                v-model="siteEditorForm.rateLimitMax"
                class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]"
              >
            </div>
          </div>

          <div>
            <h4 class="text-sm text-gray-300 mb-2">代理参数</h4>
            <div class="grid md:grid-cols-2 gap-4 text-sm text-[#aaaaaa]">
              <label class="flex flex-col">
                <span class="mb-1">连接超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyConnectTimeout"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">读取超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyReadTimeout"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">写入超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyWriteTimeout"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">连接池超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyPoolTimeout"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">Keepalive 过期 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyKeepaliveExpiry"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">最大连接数</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyMaxConnections"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">最大 Keepalive 连接数</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyMaxKeepaliveConnections"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">分块大小 (字节)</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyChunkSize"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">最大重试次数</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyMaxRetries"
                  class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-[#cc0000]">
              </label>
            </div>
            <div class="flex flex-wrap gap-4 mt-3 text-sm text-[#aaaaaa]">
              <label class="flex items-center gap-2">
                <input type="checkbox" v-model="siteEditorForm.proxyEnableHttp2" class="accent-[#cc0000]">
                启用 HTTP/2
              </label>
              <label class="flex items-center gap-2">
                <input type="checkbox" v-model="siteEditorForm.proxyFollowRedirects" class="accent-[#cc0000]">
                允许重定向
              </label>
            </div>
          </div>

          <div>
            <h4 class="text-sm text-gray-300 mb-2">登录检测</h4>
            <div class="grid md:grid-cols-2 gap-4">
              <input v-model="siteEditorForm.loginCheckUrl" placeholder="检测 URL" class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]">
              <input type="number" step="0.1" v-model="siteEditorForm.loginTimeout" placeholder="超时时间 (秒)" class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#cc0000]">
            </div>
            <textarea
              v-model="siteEditorForm.loginHeadersText"
              rows="4"
              class="w-full bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-sm mt-3 focus:outline-none focus:border-[#cc0000]"
              placeholder="登录检测请求头，每行 key: value"
            ></textarea>
          </div>

          <div class="flex flex-wrap gap-6 text-sm text-[#aaaaaa]">
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataNsfw" class="accent-[#cc0000]">
              默认标记为 NSFW
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataRequiresCookies" class="accent-[#cc0000]">
              需要 Cookies 才可抓取
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataRequiresLogin" class="accent-[#cc0000]">
              需要登录状态
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataPlayerUrlCache" class="accent-[#cc0000]">
              启用播放器链接缓存
            </label>
          </div>

          <div
            v-if="siteEditorError"
            class="text-sm text-red-400 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-2"
          >
            {{ siteEditorError }}
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-white/10">
          <button
            @click="closeSiteEditor"
            class="px-5 py-2 rounded-full bg-white/5 hover:bg-white/10 text-sm transition-colors"
          >
            取消
          </button>
          <button
            @click="saveSiteEditor"
            :disabled="siteEditorSaving"
            class="px-5 py-2 rounded-full bg-[#cc0000] hover:bg-[#ff0000] text-sm font-medium transition-colors disabled:opacity-50"
          >
            {{ siteEditorSaving ? '保存中...' : '保存配置' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, computed, watch } from 'vue';
import axios from '../utils/axios';
import { resetSitesCache } from '../composables/useSites';
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
  testSiteLoginStatus,
  testAllSitesConnectivity,
  uploadSiteCookies
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
const loginStatusResults = ref({});
const loginStatusTesting = ref({});
const cookieUploading = ref({});

// 站点配置（数据爬取）
const siteCatalog = ref({});
const siteCatalogLoading = ref(false);
const siteCatalogLoaded = ref(false);
const siteEditorVisible = ref(false);
const siteEditorSaving = ref(false);
const siteEditorError = ref('');
const siteEditorForm = ref({
  slug: '',
  siteName: '',
  label: '',
  domainsText: '',
  aliasesText: '',
  enabled: true,
  testUrl: '',
  httpHeadersText: '',
  rateLimitMin: '',
  rateLimitMax: '',
  proxyConnectTimeout: '',
  proxyReadTimeout: '',
  proxyWriteTimeout: '',
  proxyPoolTimeout: '',
  proxyKeepaliveExpiry: '',
  proxyMaxConnections: '',
  proxyMaxKeepaliveConnections: '',
  proxyChunkSize: '',
  proxyMaxRetries: '',
  proxyEnableHttp2: true,
  proxyFollowRedirects: true,
  loginCheckUrl: '',
  loginHeadersText: '',
  loginTimeout: '',
  metadataNsfw: false,
  metadataRequiresCookies: false,
  metadataRequiresLogin: false,
  metadataPlayerUrlCache: false,
});

// 计算属性
const siteStats = computed(() => ({
  total: supportedSites.value.length || 0
}));

const siteCatalogMap = computed(() => siteCatalog.value || {});

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

  const loginResultMap = loginStatusResults.value || {};
  const loginTestingMap = loginStatusTesting.value || {};

  return supportedSites.value.map(siteInfo => {
    const siteName = siteInfo.name;
    const result = resultsMap.get(siteName);
    const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || null;
    const catalogDomains = catalogInfo?.domains || [];
    const displayLabel = catalogInfo?.label || siteInfo.name;
    
    // 合并站点信息和测试结果
    return {
      ...siteInfo,
      ...result,
      site_name: siteName,
      // 优先使用站点配置中的域名，其次为测试结果、站点定义
      domains: catalogDomains.length > 0 ? catalogDomains : (result?.domains || siteInfo.domains || []),
      test_url: result?.test_url || siteInfo.test_url || '',
      loginStatus: loginResultMap[siteName],
      loginTesting: !!loginTestingMap[siteName],
      supports_login_status: siteInfo.supports_login_status ?? false,
      cookieUploading: !!cookieUploading.value[siteName],
      display_label: displayLabel,
      config_enabled: catalogInfo?.enabled !== false,
      config_aliases: catalogInfo?.aliases || [],
    };
  });
});

const parseListInput = (text = '') => {
  return text
    .split(/[\n,]/)
    .map(item => item.trim())
    .filter(Boolean);
};

const setLoginTesting = (siteName, value) => {
  if (!siteName) return;
  loginStatusTesting.value = {
    ...loginStatusTesting.value,
    [siteName]: value
  };
};

const upsertLoginStatus = (siteName, payload) => {
  if (!siteName) return;
  loginStatusResults.value = {
    ...loginStatusResults.value,
    [siteName]: payload
  };
};

const headersToText = (headers = {}) => {
  return Object.entries(headers || {})
    .map(([key, value]) => `${key}: ${value}`)
    .join('\n');
};

const parseHeadersText = (text = '') => {
  const result = {};
  text.split('\n').forEach(line => {
    const trimmed = line.trim();
    if (!trimmed) return;
    const [key, ...rest] = trimmed.split(':');
    if (!key) return;
    result[key.trim()] = rest.join(':').trim();
  });
  return result;
};

const toNumberOrUndefined = (value) => {
  if (value === '' || value === null || value === undefined) {
    return undefined;
  }
  const num = Number(value);
  return Number.isNaN(num) ? undefined : num;
};

const catalogObjectToPayload = (catalogObj) => {
  return Object.entries(catalogObj).map(([slug, info]) => {
    const payload = {
      slug,
      label: info?.label || slug,
      domains: info?.domains || [],
      aliases: info?.aliases || [],
      enabled: info?.enabled !== false,
    };
    if (info?.http) payload.http = info.http;
    if (info?.proxy) payload.proxy = info.proxy;
    if (info?.login) payload.login = info.login;
    if (info?.rate_limit) payload.rate_limit = info.rate_limit;
    if (info?.metadata) payload.metadata = info.metadata;
    if (info?.test_url) payload.test_url = info.test_url;
    return payload;
  });
};

const loadSiteCatalog = async () => {
  siteCatalogLoading.value = true;
  try {
    const resp = await axios.get('/api/sites');
    if (resp?.data?.code === 0) {
      siteCatalog.value = resp.data.data || {};
      siteCatalogLoaded.value = true;
    } else {
      siteCatalogLoaded.value = false;
    }
  } catch (error) {
    console.error('获取站点配置失败:', error);
    siteCatalogLoaded.value = false;
  } finally {
    siteCatalogLoading.value = false;
  }
};

const openSiteEditor = async (site) => {
  if (!siteCatalogLoaded.value && !siteCatalogLoading.value) {
    await loadSiteCatalog();
  }
  const siteName = site.site_name || site.name;
  const slug = (siteName || '').toLowerCase();
  const catalogInfo = siteCatalog.value[slug];
  const rateLimit = catalogInfo?.rate_limit || {};
  const proxy = catalogInfo?.proxy || {};
  const loginConfig = catalogInfo?.login || {};
  const metadata = catalogInfo?.metadata || {};

  siteEditorForm.value = {
    slug,
    siteName,
    label: catalogInfo?.label || siteName,
    domainsText: (catalogInfo?.domains?.length ? catalogInfo.domains : (site.domains || [])).join('\n'),
    aliasesText: (catalogInfo?.aliases || []).join('\n'),
    enabled: catalogInfo?.enabled !== false,
    testUrl: catalogInfo?.test_url || '',
    httpHeadersText: headersToText(catalogInfo?.http?.headers || {}),
    rateLimitMin: rateLimit?.min_interval ?? '',
    rateLimitMax: rateLimit?.max_interval ?? '',
    proxyConnectTimeout: proxy?.connect_timeout ?? '',
    proxyReadTimeout: proxy?.read_timeout ?? '',
    proxyWriteTimeout: proxy?.write_timeout ?? '',
    proxyPoolTimeout: proxy?.pool_timeout ?? '',
    proxyKeepaliveExpiry: proxy?.keepalive_expiry ?? '',
    proxyMaxConnections: proxy?.max_connections ?? '',
    proxyMaxKeepaliveConnections: proxy?.max_keepalive_connections ?? '',
    proxyChunkSize: proxy?.chunk_size ?? '',
    proxyMaxRetries: proxy?.max_retries ?? '',
    proxyEnableHttp2: proxy?.enable_http2 !== false,
    proxyFollowRedirects: proxy?.follow_redirects !== false,
    loginCheckUrl: loginConfig?.check_url || '',
    loginHeadersText: headersToText(loginConfig?.headers || {}),
    loginTimeout: loginConfig?.timeout ?? '',
    metadataNsfw: !!metadata?.nsfw,
    metadataRequiresCookies: !!metadata?.requires_cookies,
    metadataRequiresLogin: !!metadata?.requires_login,
    metadataPlayerUrlCache: !!metadata?.player_url_cache,
  };
  siteEditorError.value = '';
  siteEditorVisible.value = true;
};

const closeSiteEditor = () => {
  siteEditorVisible.value = false;
  siteEditorError.value = '';
};

const saveSiteEditor = async () => {
  siteEditorError.value = '';
  const { slug, siteName } = siteEditorForm.value;
  if (!slug) {
    siteEditorError.value = '站点标识不可为空';
    return;
  }
  const domains = parseListInput(siteEditorForm.value.domainsText);
  if (!domains.length) {
    siteEditorError.value = '请至少填写一个域名';
    return;
  }
  const aliases = parseListInput(siteEditorForm.value.aliasesText);
  const label = siteEditorForm.value.label?.trim() || siteName || slug;

  const httpHeaders = parseHeadersText(siteEditorForm.value.httpHeadersText);
  const loginHeaders = parseHeadersText(siteEditorForm.value.loginHeadersText);
  const rateLimitMin = toNumberOrUndefined(siteEditorForm.value.rateLimitMin);
  const rateLimitMax = toNumberOrUndefined(siteEditorForm.value.rateLimitMax);
  const proxyPayload = {};
  const proxyFields = [
    ['connect_timeout', siteEditorForm.value.proxyConnectTimeout],
    ['read_timeout', siteEditorForm.value.proxyReadTimeout],
    ['write_timeout', siteEditorForm.value.proxyWriteTimeout],
    ['pool_timeout', siteEditorForm.value.proxyPoolTimeout],
    ['keepalive_expiry', siteEditorForm.value.proxyKeepaliveExpiry],
    ['max_connections', siteEditorForm.value.proxyMaxConnections],
    ['max_keepalive_connections', siteEditorForm.value.proxyMaxKeepaliveConnections],
    ['chunk_size', siteEditorForm.value.proxyChunkSize],
    ['max_retries', siteEditorForm.value.proxyMaxRetries],
  ];
  proxyFields.forEach(([key, value]) => {
    const num = toNumberOrUndefined(value);
    if (num !== undefined) {
      proxyPayload[key] = num;
    }
  });
  proxyPayload.enable_http2 = !!siteEditorForm.value.proxyEnableHttp2;
  proxyPayload.follow_redirects = !!siteEditorForm.value.proxyFollowRedirects;

  const rateLimitPayload = {};
  if (rateLimitMin !== undefined) rateLimitPayload.min_interval = rateLimitMin;
  if (rateLimitMax !== undefined) rateLimitPayload.max_interval = rateLimitMax;

  const loginPayload = {};
  if (siteEditorForm.value.loginCheckUrl?.trim()) {
    loginPayload.check_url = siteEditorForm.value.loginCheckUrl.trim();
  }
  if (Object.keys(loginHeaders).length) {
    loginPayload.headers = loginHeaders;
  }
  const loginTimeout = toNumberOrUndefined(siteEditorForm.value.loginTimeout);
  if (loginTimeout !== undefined) {
    loginPayload.timeout = loginTimeout;
  }

  const metadataPayload = {
    nsfw: !!siteEditorForm.value.metadataNsfw,
    requires_cookies: !!siteEditorForm.value.metadataRequiresCookies,
    requires_login: !!siteEditorForm.value.metadataRequiresLogin,
    player_url_cache: !!siteEditorForm.value.metadataPlayerUrlCache,
  };

  const sitePayload = {
    label,
    domains,
    aliases,
    enabled: !!siteEditorForm.value.enabled,
  };
  const testUrl = siteEditorForm.value.testUrl?.trim();
  if (testUrl) {
    sitePayload.test_url = testUrl;
  }
  if (Object.keys(httpHeaders).length) {
    sitePayload.http = { headers: httpHeaders };
  }
  if (Object.keys(rateLimitPayload).length) {
    sitePayload.rate_limit = rateLimitPayload;
  }
  if (Object.keys(proxyPayload).some(key => proxyPayload[key] !== undefined && proxyPayload[key] !== '')) {
    sitePayload.proxy = proxyPayload;
  }
  if (Object.keys(loginPayload).length) {
    sitePayload.login = loginPayload;
  }
  sitePayload.metadata = metadataPayload;

  const updatedCatalog = { ...siteCatalog.value };
  updatedCatalog[slug] = sitePayload;

  siteEditorSaving.value = true;
  try {
    const payload = catalogObjectToPayload(updatedCatalog);
    const resp = await axios.put('/api/sites', { sites: payload });
    if (resp?.data?.code !== 0) {
      throw new Error(resp?.data?.msg || '保存站点配置失败');
    }
    siteCatalog.value = resp.data.data || {};
    resetSitesCache();
    siteEditorVisible.value = false;
  } catch (error) {
    console.error('保存站点配置失败:', error);
    siteEditorError.value = error?.message || '保存站点配置失败';
  } finally {
    siteEditorSaving.value = false;
  }
};

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

const handleTestLogin = async (site) => {
  const siteName = site.site_name || site.name;
  setLoginTesting(siteName, true);

  const result = await testSiteLoginStatus(siteName);

  if (result.success && result.data) {
    upsertLoginStatus(siteName, result.data);
  } else {
    upsertLoginStatus(siteName, {
      site_name: siteName,
      logged_in: false,
      message: result.error || '检测失败',
      supported: false,
      checked_at: new Date().toISOString(),
    });
  }

  setLoginTesting(siteName, false);
};

const setCookieUploading = (siteName, value) => {
  cookieUploading.value = {
    ...cookieUploading.value,
    [siteName]: value
  };
};

const handleUploadCookies = (site) => {
  const siteName = site.site_name || site.name;
  const input = document.createElement('input');
  input.type = 'file';
  input.accept = '.txt,.json';

  input.onchange = async (event) => {
    const files = event.target.files || [];
    if (!files.length) {
      return;
    }

    const file = files[0];
    setCookieUploading(siteName, true);
    try {
      const result = await uploadSiteCookies(siteName, file);
      if (result.success && result.data?.login_status) {
        loginStatusResults.value = {
          ...loginStatusResults.value,
          [siteName]: result.data.login_status
        };
      }
    } finally {
      setCookieUploading(siteName, false);
    }
    input.value = '';
  };

  input.click();
};

const testLoginForAllSupportedSites = async () => {
  const targets = supportedSites.value.filter(site => site.supports_login_status);
  if (!targets.length) return;

  await Promise.all(
    targets.map(async (site) => {
      const siteName = site.site_name || site.name;
      if (!siteName) return;

      setLoginTesting(siteName, true);
      try {
        const result = await testSiteLoginStatus(siteName);
        if (result.success && result.data) {
          upsertLoginStatus(siteName, result.data);
        } else {
          upsertLoginStatus(siteName, {
            site_name: siteName,
            logged_in: false,
            message: result.error || '检测失败',
            supported: false,
            checked_at: new Date().toISOString(),
          });
        }
      } finally {
        setLoginTesting(siteName, false);
      }
    })
  );
};

// 测试全部站点
const handleTestAll = async () => {
  testingAll.value = true;
  try {
    const result = await testAllSitesConnectivity();
    if (result.success && result.data) {
      connectivityResults.value = [result.data];
    }
    await testLoginForAllSupportedSites();
  } finally {
    testingAll.value = false;
  }
};

// 监听标签页切换
watch(currentTab, async (newTab) => {
  if (newTab === 'connectivity' && supportedSites.value.length === 0) {
    await fetchSupportedSites();
  }
});

onMounted(() => {
  fetchPlugins();
  loadSiteCatalog();
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

.site-editor-scroll::-webkit-scrollbar {
  width: 8px;
}

.site-editor-scroll::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.05);
  border-radius: 9999px;
}

.site-editor-scroll::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.15);
  border-radius: 9999px;
}

.site-editor-scroll:hover::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
}
</style>


