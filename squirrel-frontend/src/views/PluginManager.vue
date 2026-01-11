<template>
  <div class="plugin-manager bg-bg-primary text-text-primary h-full flex flex-col min-h-0">
    <!-- 顶部操作区 -->
    <div class="toolbar-container pt-6 pb-4">
      <div class="flex flex-col gap-4">
        <div>
          <h1 class="text-2xl font-semibold text-text-primary">插件管理</h1>
          <p class="text-sm text-text-muted mt-1">导入、启用或卸载插件，控制后端扩展能力。</p>
        </div>
        <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <!-- 标签页切换 -->
          <div class="inline-flex items-center gap-1 p-1 rounded-full bg-bg-secondary border border-border-primary">
            <button
              @click="currentTab = 'plugins'"
              class="px-4 py-2 text-sm font-medium rounded-full transition-colors"
              :class="currentTab === 'plugins' ? 'bg-bg-elevated text-text-primary shadow-sm' : 'text-text-muted hover:text-text-primary hover:bg-bg-hover'"
            >
              插件列表
            </button>
            <button
              @click="currentTab = 'connectivity'"
              class="px-4 py-2 text-sm font-medium rounded-full transition-colors"
              :class="currentTab === 'connectivity' ? 'bg-bg-elevated text-text-primary shadow-sm' : 'text-text-muted hover:text-text-primary hover:bg-bg-hover'"
            >
              站点连通性
            </button>
          </div>
          <div class="flex flex-wrap items-center gap-2">
            <template v-if="currentTab === 'plugins'">
              <label class="flex items-center gap-2 px-4 py-2 bg-bg-secondary border border-border-primary hover:bg-bg-hover rounded-full cursor-pointer transition-colors">
                <input
                  type="file"
                  accept=".zip"
                  class="hidden"
                  @change="handleFileChange"
                />
                <CloudArrowUpIcon class="w-5 h-5" />
                <span class="text-sm font-medium">{{ selectedFile ? selectedFile.name : '选择文件' }}</span>
              </label>
              <button
                class="px-4 py-2 bg-color-error hover:bg-color-error-hover rounded-full text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                :disabled="!selectedFile || installing"
                @click="handleInstall"
              >
                {{ installing ? '安装中...' : '导入插件' }}
              </button>
              <button
                class="p-2 bg-bg-secondary border border-border-primary hover:bg-bg-hover rounded-full transition-colors disabled:opacity-40"
                :disabled="reloading || loading"
                @click="handleReload"
                title="重新加载插件"
              >
                <ArrowPathIcon class="w-5 h-5" :class="{ 'animate-spin': reloading }" />
              </button>
            </template>
            <template v-else>
              <label class="flex items-center gap-2 px-3 py-2 bg-bg-elevated border border-border-secondary hover:bg-bg-hover rounded-full cursor-pointer transition-colors text-xs md:text-sm">
                <input
                  type="file"
                  accept=".txt"
                  class="hidden"
                  @change="handleCookiesFileChange"
                />
                <span class="truncate max-w-[180px]" :title="cookiesFileName || '选择 cookies.txt 文件'">
                  {{ cookiesFileName || '选择 cookies.txt 文件' }}
                </span>
              </label>
              <button
                @click="handleImportAllCookies"
                :disabled="!selectedCookiesFile || importingCookies"
                class="px-3 py-2 bg-bg-elevated border border-border-secondary hover:bg-bg-hover rounded-full text-xs md:text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {{ importingCookies ? '导入中...' : '导入所有站点 Cookie' }}
              </button>
              <button
                @click="handleSyncCookieCloud"
                :disabled="syncingCookieCloud"
                class="px-3 py-2 bg-bg-elevated border border-border-secondary hover:bg-bg-hover rounded-full text-xs md:text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {{ syncingCookieCloud ? '同步中...' : '从 CookieCloud 同步' }}
              </button>
              <button
                @click="handleTestAll"
                :disabled="testingAll || loadingSites"
                class="px-4 py-2 bg-color-error hover:bg-color-error-hover rounded-full text-sm font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <ArrowPathIcon v-if="testingAll" class="w-4 h-4 animate-spin" />
                <CheckCircleIcon v-else class="w-4 h-4" />
                {{ testingAll ? '测试中...' : '测试全部' }}
              </button>
            </template>
          </div>
        </div>
      </div>
    </div>

    <div class="content-container pb-10 flex-1 min-h-0 space-y-6">
      <!-- 插件列表 -->
      <div v-if="currentTab === 'plugins'" class="space-y-4">
        <div v-if="loading" class="bg-bg-secondary border border-border-primary rounded-lg flex items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-2 border-text-muted border-t-text-primary"></div>
        </div>

        <div v-else-if="plugins.length === 0" class="bg-bg-secondary border border-border-primary rounded-lg flex flex-col items-center justify-center py-20 text-text-muted">
          <CubeIcon class="w-16 h-16 mb-4 opacity-40" />
          <p class="text-sm">暂无插件</p>
          <p class="text-xs mt-1">请导入插件 ZIP 包</p>
        </div>

        <div v-else class="bg-bg-secondary border border-border-primary rounded-lg overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-border-secondary">
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-muted">名称</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-muted">版本</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-muted">来源</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-muted hidden lg:table-cell">描述</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-text-muted">状态</th>
                  <th class="text-right py-3 px-4 text-sm font-medium text-text-muted">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="plugin in plugins"
                  :key="plugin.name"
                  class="border-b border-border-primary hover:bg-bg-hover transition-colors"
                >
                  <td class="py-4 px-4">
                    <div>
                      <div class="flex items-center gap-2">
                        <span class="font-medium">{{ plugin.name }}</span>
                        <span
                          v-if="plugin.state === 'missing'"
                          class="px-2 py-0.5 text-2xs rounded bg-color-error/20 text-color-error font-medium"
                        >
                          配置缺失
                        </span>
                        <span
                          v-else-if="plugin.source === 'external'"
                          class="px-2 py-0.5 text-2xs rounded bg-color-info/20 text-color-info font-medium"
                        >
                          外部
                        </span>
                        <span
                          v-else-if="plugin.source === 'internal'"
                          class="px-2 py-0.5 text-2xs rounded bg-color-warning/20 text-color-warning font-medium"
                        >
                          内置
                        </span>
                      </div>
                      <div v-if="plugin.module" class="text-xs text-text-muted mt-0.5">{{ plugin.module }}</div>
                    </div>
                  </td>
                  <td class="py-4 px-4 text-text-muted text-sm">{{ plugin.version || '—' }}</td>
                  <td class="py-4 px-4 text-text-muted text-sm">{{ formatSource(plugin.source) }}</td>
                  <td class="py-4 px-4 text-text-muted text-sm hidden lg:table-cell max-w-md">
                    <div class="line-clamp-2">{{ plugin.description || '暂无描述' }}</div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex justify-center">
                      <span
                        class="px-2.5 py-1 rounded text-xs font-medium"
                        :class="plugin.enabled ? 'bg-color-success/20 text-color-success' : 'bg-bg-tertiary text-text-muted'"
                      >
                        {{ plugin.enabled ? '已启用' : '已禁用' }}
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex items-center justify-end gap-2">
                      <button
                        v-if="!plugin.enabled"
                        class="px-3 py-1.5 bg-bg-elevated hover:bg-bg-hover rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        :disabled="actioning === plugin.name || plugin.state === 'missing'"
                        @click="handleEnable(plugin)"
                      >
                        启用
                      </button>
                      <button
                        v-if="plugin.enabled"
                        class="px-3 py-1.5 bg-bg-tertiary hover:bg-bg-hover rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                        :disabled="actioning === plugin.name || plugin.state === 'missing'"
                        @click="handleDisable(plugin)"
                      >
                        禁用
                      </button>
                      <button
                        v-if="plugin.source === 'external'"
                        class="px-3 py-1.5 bg-bg-tertiary hover:bg-color-error/20 hover:text-color-error rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
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

      <!-- 站点连通性测试 -->
      <div v-if="currentTab === 'connectivity'" class="space-y-4">

        <!-- 统计信息 -->
        <div v-if="connectivityResults.length > 0" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatsCard title="总站点数" :value="connectivitySummary.total" :hover-effect="true" />
          <StatsCard title="可访问" :value="connectivitySummary.accessible" value-color="success" :hover-effect="true" />
          <StatsCard title="不可访问" :value="connectivitySummary.failed" value-color="error" :hover-effect="true" />
          <StatsCard title="成功率" :value="connectivitySummary.success_rate" format="percentage" value-color="success" :hover-effect="true" />
        </div>

        <!-- 加载状态 -->
        <div v-if="loadingSites" class="bg-bg-secondary border border-border-primary rounded-lg flex items-center justify-center py-20">
          <div class="animate-spin rounded-full h-8 w-8 border-2 border-text-muted border-t-text-primary"></div>
        </div>

        <!-- 站点列表 -->
        <div v-else class="bg-bg-secondary border border-border-primary rounded-lg overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full">
              <thead>
                <tr class="border-b border-border-secondary">
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-muted">站点名称</th>
                  <th class="text-left py-3 px-4 text-sm font-medium text-text-muted hidden lg:table-cell">支持域名</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-text-muted">状态</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-text-muted">登录状态</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-text-muted">响应时间</th>
                  <th class="text-center py-3 px-4 text-sm font-medium text-text-muted hidden md:table-cell">IP地址</th>
                  <th class="text-right py-3 px-4 text-sm font-medium text-text-muted">操作</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="site in displaySites"
                  :key="site.site_name"
                  class="border-b border-border-primary hover:bg-bg-hover transition-colors"
                >
                  <td class="py-4 px-4">
                    <div class="font-medium flex items-center gap-2">
                      <span>{{ site.display_label || site.site_name || site.name }}</span>
                      <span
                        v-if="site.config_enabled === false"
                        class="px-2 py-0.5 text-2xs rounded-full bg-color-error/10 text-color-error border border-color-error/30"
                      >
                        已禁用
                      </span>
                    </div>
                    <div class="text-xs text-text-muted mt-0.5">
                      标识：{{ site.site_name || site.name }}
                    </div>
                    <div v-if="site.test_url" class="text-xs text-text-muted mt-0.5">{{ site.test_url }}</div>
                  </td>
                  <td class="py-4 px-4 hidden lg:table-cell">
                    <div class="flex flex-wrap gap-1">
                      <span
                        v-for="domain in site.domains?.slice(0, 3) || []"
                        :key="domain"
                        class="px-2 py-0.5 text-2xs rounded bg-bg-tertiary text-text-muted"
                      >
                        {{ domain }}
                      </span>
                      <span
                        v-if="site.domains?.length > 3"
                        class="px-2 py-0.5 text-2xs rounded bg-bg-tertiary text-text-muted"
                      >
                        +{{ site.domains.length - 3 }}
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex justify-center">
                      <span
                        v-if="site.testing"
                        class="px-2.5 py-1 rounded text-xs font-medium bg-color-info/20 text-color-info flex items-center gap-1"
                      >
                        <ArrowPathIcon class="w-3 h-3 animate-spin" />
                        测试中
                      </span>
                      <span
                        v-else-if="site.accessible === true"
                        class="px-2.5 py-1 rounded text-xs font-medium bg-color-success/20 text-color-success"
                      >
                        ✓ 可访问
                      </span>
                      <span
                        v-else-if="site.accessible === false"
                        class="px-2.5 py-1 rounded text-xs font-medium bg-color-error/20 text-color-error"
                        :title="site.error_message"
                      >
                        ✗ 不可访问
                      </span>
                      <span
                        v-else
                        class="px-2.5 py-1 rounded text-xs font-medium bg-bg-tertiary text-text-muted"
                      >
                        未测试
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex justify-center">
                      <span
                        v-if="!site.supports_login_status"
                        class="px-2.5 py-1 rounded text-xs font-medium bg-bg-tertiary text-text-muted"
                      >
                        未接入
                      </span>
                      <span
                        v-else-if="site.loginTesting"
                        class="px-2.5 py-1 rounded text-xs font-medium bg-color-info/20 text-color-info flex items-center gap-1"
                      >
                        <ArrowPathIcon class="w-3 h-3 animate-spin" />
                        检测中
                      </span>
                      <span
                        v-else-if="site.loginStatus?.logged_in"
                        class="px-2.5 py-1 rounded text-xs font-medium bg-color-success/20 text-color-success"
                        :title="site.loginStatus?.message || '已登录'"
                      >
                        已登录
                      </span>
                      <span
                        v-else-if="site.loginStatus"
                        class="px-2.5 py-1 rounded text-xs font-medium bg-color-error/20 text-color-error"
                        :title="site.loginStatus?.message || '未登录'"
                      >
                        未登录
                      </span>
                      <span
                        v-else
                        class="px-2.5 py-1 rounded text-xs font-medium bg-bg-tertiary text-text-muted"
                      >
                        未检测
                      </span>
                    </div>
                  </td>
                  <td class="py-4 px-4 text-center text-sm text-text-muted">
                    {{ site.response_time ? `${site.response_time}ms` : '—' }}
                  </td>
                  <td class="py-4 px-4 text-center text-sm text-text-muted hidden md:table-cell">
                    {{ site.ip_address || '—' }}
                  </td>
                  <td class="py-4 px-4">
                    <div class="flex items-center justify-end gap-2">
                      <button
                        @click="handleTestSingle(site)"
                        :disabled="site.testing || testingAll"
                        class="px-3 py-1.5 bg-bg-elevated hover:bg-bg-hover rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        {{ site.testing ? '测试中...' : '连通性' }}
                      </button>
                      <button
                        v-if="site.supports_login_status"
                        @click="handleTestLogin(site)"
                        :disabled="site.loginTesting || testingAll"
                        class="px-3 py-1.5 bg-bg-tertiary hover:bg-bg-hover rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                      >
                        {{ site.loginTesting ? '检测中...' : '登录检测' }}
                      </button>
                      <button
                        @click="handleUploadCookies(site)"
                        :disabled="site.cookieUploading || testingAll"
                        class="px-3 py-1.5 bg-bg-tertiary hover:bg-bg-hover rounded-full text-xs font-medium transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
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
      </div>
    </div>

    <!-- 站点配置编辑弹窗 -->
    <div
      v-if="siteEditorVisible"
      class="fixed inset-0 bg-overlay-dark-70 flex items-center justify-center z-50 p-4"
    >
      <div class="bg-bg-secondary rounded-2xl border border-border-primary w-full max-w-3xl shadow-2xl">
        <div class="flex items-center justify-between px-6 py-4 border-b border-border-secondary">
          <div>
            <h3 class="text-lg font-semibold">编辑站点配置</h3>
            <p class="text-xs text-text-muted mt-1">插件站点：{{ siteEditorForm.siteName }}</p>
          </div>
          <button
            class="text-text-muted hover:text-text-primary transition-colors"
            @click="closeSiteEditor"
          >
            ✕
          </button>
        </div>

        <div class="site-editor-scroll px-6 py-5 space-y-5 max-h-[70vh] overflow-y-auto pr-2">
          <div>
            <label class="block text-sm text-text-muted mb-1">显示名称</label>
            <input
              v-model="siteEditorForm.label"
              class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error"
              placeholder="展示给用户的名称"
            >
          </div>

  <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-text-muted mb-1">域名列表</label>
              <textarea
                v-model="siteEditorForm.domainsText"
                rows="5"
                class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error"
                placeholder="每行一个域名，例如：www.youtube.com"
              ></textarea>
              <p class="text-xs text-text-tertiary mt-1">用于匹配订阅与视频来源，至少填写一个域名。</p>
            </div>
            <div>
              <label class="block text-sm text-text-muted mb-1">别名（可选）</label>
              <textarea
                v-model="siteEditorForm.aliasesText"
                rows="5"
                class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error"
                placeholder="每行一个别名，例如：yt、油管"
              ></textarea>
              <p class="text-xs text-text-tertiary mt-1">别名可用于筛选条件。</p>
            </div>
          </div>

          <div class="flex items-center gap-3 text-sm text-text-muted">
            <label class="flex items-center gap-2 cursor-pointer select-none">
              <input type="checkbox" v-model="siteEditorForm.enabled" class="accent-color-error">
              启用该站点（用于筛选/数据爬取）
            </label>
          </div>

          <div>
            <label class="block text-sm text-text-muted mb-1">测试 URL</label>
            <input
              v-model="siteEditorForm.testUrl"
              class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error"
              placeholder="用于连通性检测的 URL"
            >
          </div>

          <div>
            <label class="block text-sm text-text-muted mb-1">HTTP 请求头（每行 key: value）</label>
            <textarea
              v-model="siteEditorForm.httpHeadersText"
              rows="4"
              class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error"
              placeholder="User-Agent: Mozilla/5.0"
            ></textarea>
          </div>

          <div class="grid md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-text-muted mb-1">最小请求间隔（秒）</label>
              <input
                type="number"
                step="0.1"
                v-model="siteEditorForm.rateLimitMin"
                class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error"
              >
            </div>
            <div>
              <label class="block text-sm text-text-muted mb-1">最大请求间隔（秒）</label>
              <input
                type="number"
                step="0.1"
                v-model="siteEditorForm.rateLimitMax"
                class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error"
              >
            </div>
          </div>

          <div>
            <h4 class="text-sm text-text-secondary mb-2">代理参数</h4>
            <div class="grid md:grid-cols-2 gap-4 text-sm text-text-muted">
              <label class="flex flex-col">
                <span class="mb-1">连接超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyConnectTimeout"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">读取超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyReadTimeout"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">写入超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyWriteTimeout"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">连接池超时 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyPoolTimeout"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">Keepalive 过期 (秒)</span>
                <input type="number" step="0.1" v-model="siteEditorForm.proxyKeepaliveExpiry"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">最大连接数</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyMaxConnections"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">最大 Keepalive 连接数</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyMaxKeepaliveConnections"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">分块大小 (字节)</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyChunkSize"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
              <label class="flex flex-col">
                <span class="mb-1">最大重试次数</span>
                <input type="number" step="1" v-model="siteEditorForm.proxyMaxRetries"
                  class="w-full bg-bg-tertiary border border-border-primary rounded-lg px-3 py-2 focus:outline-none focus:border-color-error focus:ring-1 focus:ring-color-error">
              </label>
            </div>
            <div class="flex flex-wrap gap-4 mt-3 text-sm text-text-muted">
              <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.proxyEnableHttp2" class="accent-color-error">
                启用 HTTP/2
              </label>
              <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.proxyFollowRedirects" class="accent-color-error">
                允许重定向
              </label>
            </div>
          </div>

          <div>
            <h4 class="text-sm text-text-secondary mb-2">登录检测</h4>
            <div class="grid md:grid-cols-2 gap-4">
              <input v-model="siteEditorForm.loginCheckUrl" placeholder="检测 URL" class="w-full bg-bg-tertiary border border-border-secondary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error">
              <input type="number" step="0.1" v-model="siteEditorForm.loginTimeout" placeholder="超时时间 (秒)" class="w-full bg-bg-tertiary border border-border-secondary rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-color-error">
            </div>
            <textarea
              v-model="siteEditorForm.loginHeadersText"
              rows="4"
              class="w-full bg-bg-tertiary border border-border-secondary rounded-lg px-3 py-2 text-sm mt-3 focus:outline-none focus:border-color-error"
              placeholder="登录检测请求头，每行 key: value"
            ></textarea>
          </div>

          <div class="flex flex-wrap gap-6 text-sm text-text-muted">
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataNsfw" class="accent-color-error">
              默认标记为 NSFW
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataRequiresCookies" class="accent-color-error">
              需要 Cookies 才可抓取
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataRequiresLogin" class="accent-color-error">
              需要登录状态
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataPlayerUrlCache" class="accent-color-error">
              启用播放器链接缓存
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataOfflineThumbnailsDownload" class="accent-color-error">
              解析时下载封面到本地
            </label>
            <label class="flex items-center gap-2">
              <input type="checkbox" v-model="siteEditorForm.metadataOfflineThumbnailsDisplay" class="accent-color-error">
              优先使用本地封面显示
            </label>
          </div>

          <div
            v-if="siteEditorError"
            class="text-sm text-color-error bg-color-error/10 border border-color-error/30 rounded-lg px-4 py-2"
          >
            {{ siteEditorError }}
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-border-secondary">
          <button
            @click="closeSiteEditor"
            class="px-5 py-2 rounded-full bg-bg-tertiary hover:bg-bg-hover text-sm transition-colors"
          >
            取消
          </button>
          <button
            @click="saveSiteEditor"
            :disabled="siteEditorSaving"
            class="px-5 py-2 rounded-full bg-color-error hover:bg-color-error-hover text-sm font-medium transition-colors disabled:opacity-50"
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
import {
  CloudArrowUpIcon,
  ArrowPathIcon,
  CubeIcon,
  CheckCircleIcon
} from '@heroicons/vue/24/outline';
import StatsCard from '../components/common/StatsCard.vue';
import axios from '../utils/axios';
import { resetSitesCache } from '../composables/useSites';
import { usePluginApi } from '../composables/usePluginApi';
import { formatDate } from '../utils/dateFormat';

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
  importAllSiteCookies,
  uploadSiteCookies,
  syncCookieCloudCookies,
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
const lastTestedAt = ref(null);

// 缓存相关常量
const CACHE_KEY_CONNECTIVITY = 'squirrel_connectivity_results';
const CACHE_KEY_LOGIN_STATUS = 'squirrel_login_status_results';
const CACHE_KEY_LAST_TESTED = 'squirrel_last_tested_at';

// 缓存函数
const saveResultsToCache = () => {
  try {
    if (connectivityResults.value.length > 0) {
      localStorage.setItem(CACHE_KEY_CONNECTIVITY, JSON.stringify(connectivityResults.value));
    }
    if (Object.keys(loginStatusResults.value).length > 0) {
      localStorage.setItem(CACHE_KEY_LOGIN_STATUS, JSON.stringify(loginStatusResults.value));
    }
    const now = new Date().toISOString();
    lastTestedAt.value = now;
    localStorage.setItem(CACHE_KEY_LAST_TESTED, now);
  } catch (e) {
    console.warn('保存连通性缓存失败:', e);
  }
};

const loadResultsFromCache = () => {
  try {
    const cachedConnectivity = localStorage.getItem(CACHE_KEY_CONNECTIVITY);
    const cachedLoginStatus = localStorage.getItem(CACHE_KEY_LOGIN_STATUS);
    const cachedLastTested = localStorage.getItem(CACHE_KEY_LAST_TESTED);
    
    if (cachedConnectivity) {
      connectivityResults.value = JSON.parse(cachedConnectivity);
    }
    if (cachedLoginStatus) {
      loginStatusResults.value = JSON.parse(cachedLoginStatus);
    }
    if (cachedLastTested) {
      lastTestedAt.value = cachedLastTested;
    }
  } catch (e) {
    console.warn('加载连通性缓存失败:', e);
  }
};

// Cookies 导入（全局 / 单站点复用）
const selectedCookiesFile = ref(null);
const cookiesFileName = ref('');
const importingCookies = ref(false);
const syncingCookieCloud = ref(false);

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
  metadataOfflineThumbnailsDownload: false,
  metadataOfflineThumbnailsDisplay: false,
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

const handleCookiesFileChange = (event) => {
  const file = event.target.files?.[0];
  selectedCookiesFile.value = file || null;
  cookiesFileName.value = file ? file.name : '';
};

const handleImportAllCookies = async () => {
  if (!selectedCookiesFile.value || importingCookies.value) return;
  importingCookies.value = true;
  try {
    await importAllSiteCookies(selectedCookiesFile.value);
  } catch (e) {
    console.error('导入所有站点 Cookies 失败:', e);
  } finally {
    importingCookies.value = false;
  }
};

const handleSyncCookieCloud = async () => {
  if (syncingCookieCloud.value) return;
  syncingCookieCloud.value = true;
  try {
    const result = await syncCookieCloudCookies();
    if (!result?.success) {
      alert(result?.error || 'CookieCloud 同步失败');
      return;
    }
    const updatedSites = result?.data?.updated_sites ?? 0;
    alert(`CookieCloud 同步完成，更新 ${updatedSites} 个站点`);
  } catch (e) {
    console.error('CookieCloud 同步失败:', e);
    alert('CookieCloud 同步失败');
  } finally {
    syncingCookieCloud.value = false;
  }
};

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
    metadataOfflineThumbnailsDownload: !!metadata?.offline_thumbnails_download,
    metadataOfflineThumbnailsDisplay: !!metadata?.offline_thumbnails_display,
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
    offline_thumbnails_download: !!siteEditorForm.value.metadataOfflineThumbnailsDownload,
    offline_thumbnails_display: !!siteEditorForm.value.metadataOfflineThumbnailsDisplay,
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
    saveResultsToCache();
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
  saveResultsToCache();
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
    saveResultsToCache();
  } finally {
    testingAll.value = false;
  }
};

// 监听标签页切换
watch(currentTab, async (newTab) => {
  if (newTab === 'connectivity') {
    // 加载缓存的结果
    if (connectivityResults.value.length === 0) {
      loadResultsFromCache();
    }
    // 获取站点列表
    if (supportedSites.value.length === 0) {
      await fetchSupportedSites();
    }
    // 自动触发测试刷新数据
    if (!testingAll.value && supportedSites.value.length > 0) {
      handleTestAll();
    }
  }
});

onMounted(() => {
  fetchPlugins();
  loadSiteCatalog();
});
</script>

<style scoped>
.toolbar-container,
.content-container {
  max-width: var(--container-max-width, 2560px);
  margin: 0 auto;
  padding-left: 1rem;
  padding-right: 1rem;
  width: 100%;
}

@media (min-width: 640px) {
  .toolbar-container,
  .content-container {
    padding-left: 1.5rem;
    padding-right: 1.5rem;
  }
}

@media (min-width: 1024px) {
  .toolbar-container,
  .content-container {
    padding-left: 2rem;
    padding-right: 2rem;
  }
}

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
  background: var(--border-primary);
  border-radius: 9999px;
}

.site-editor-scroll::-webkit-scrollbar-thumb {
  background: var(--border-hover);
  border-radius: 9999px;
}

.site-editor-scroll:hover::-webkit-scrollbar-thumb {
  background: var(--overlay-light-30);
}
</style>
