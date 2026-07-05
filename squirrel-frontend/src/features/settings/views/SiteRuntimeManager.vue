<template>
  <AppPageShell variant="compact">
    <AppTwoColumnLayout>
      <template #sidebar>
        <div class="flex h-14 shrink-0 items-center justify-between app-divider-bottom px-4">
          <div class="min-w-0">
            <h1 class="app-h3 truncate">站点</h1>
            <p class="mt-0.5 text-xs text-muted-foreground">{{ siteRuntimeSummary.total }} 个已安装</p>
          </div>
          <Button variant="ghost" size="icon-sm" :disabled="reloading || loading" @click="handleReload">
            <AppSpinner v-if="reloading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </Button>
        </div>

        <div class="grid shrink-0 grid-cols-2 gap-2 app-divider-bottom p-3">
          <div class="app-stat-card">
            <div class="app-stat-card__label">运行</div>
            <div class="app-stat-card__value">{{ siteRuntimeSummary.running }}</div>
          </div>
          <div class="app-stat-card">
            <div class="app-stat-card__label">需关注</div>
            <div class="app-stat-card__value">{{ siteRuntimeSummary.attention }}</div>
          </div>
          <div class="app-stat-card col-span-2">
            <div class="flex items-center justify-between">
              <span class="text-xs text-muted-foreground">网络连通</span>
              <span class="text-sm font-semibold tabular-nums">{{ connectivitySummary.accessible }}/{{ connectivitySummary.total }}</span>
            </div>
            <p v-if="lastTestedAt" class="mt-1 text-xs text-muted-foreground">最近检测 {{ formatTime(lastTestedAt) }}</p>
          </div>
        </div>

        <div class="space-y-4 app-divider-bottom p-3">
          <div class="space-y-2">
            <div class="text-xs font-medium text-muted-foreground">登录凭据</div>
            <Button as-child variant="outline" class="w-full justify-start">
              <label class="cursor-pointer">
                <input type="file" accept=".txt,.json" class="hidden" @change="handleCookiesFileChange" />
                <AppIcon name="cookie" class="h-4 w-4" />
                <span class="truncate">{{ cookiesFileName || '选择凭据文件' }}</span>
              </label>
            </Button>
            <Button v-if="selectedCookiesFile" class="w-full" :disabled="importingCookies" @click="handleImportAllCookies">
              <AppSpinner v-if="importingCookies" size="sm" />
              <AppIcon v-else name="refresh" class="h-4 w-4" />
              导入凭据
            </Button>
          </div>
        </div>

        <div class="space-y-2 p-3">
          <Button variant="outline" class="w-full justify-start" :disabled="testingAll" @click="handleTestAll">
            <AppSpinner v-if="testingAll" size="sm" />
            <AppIcon v-else name="sync" class="h-4 w-4" />
            测试全部
          </Button>
        </div>
      </template>

      <template #header>
        <div class="min-w-0">
          <h2 class="app-h2 truncate">站点</h2>
          <p class="mt-0.5 text-xs text-muted-foreground">{{ siteRuntimeSummary.total }} 个站点 · {{ siteRuntimeSummary.running }} 个运行</p>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <div class="relative w-80">
            <AppIcon name="search" class="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <Input
              v-model="searchQuery"
              placeholder="搜索站点、站点或描述"
              class="pl-9 pr-8"
            />
            <button
              v-if="searchQuery"
              @click="searchQuery = ''"
              class="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/70 transition-colors hover:text-foreground"
            >
              <AppIcon name="close" class="h-4 w-4" />
            </button>
          </div>
        </div>
      </template>

      <SiteRuntimeTable
        :runtimes="displaySiteRuntimes"
        :loading="isInitialLoading"
        :actioning="actioning"
        :search-query="searchQuery"
        :discovery-errors="discoveryErrors"
        @enable="handleEnable"
        @disable="handleDisable"
        @test-connectivity="handleTestSingleBySite"
        @test-login="handleTestLoginBySite"
        @desktop-login="handleDesktopSiteLogin"
        @clear-desktop-session="handleClearDesktopSiteSession"
        @start-oauth="handleStartYouTubeOAuth"
        @revoke-oauth="handleRevokeYouTubeOAuth"
        @edit-site="openSiteEditorByRuntime"
      />

      <SiteConfigEditorDialog
        :visible="siteEditorVisible"
        :site="editingSite"
        :catalog="siteCatalog"
        :saving="siteEditorSaving"
        :error-message="siteEditorError"
        @close="closeSiteEditor"
        @save="saveSiteEditor"
      />

      <YouTubeOAuthPrompt
        :prompt="youtubeOAuthPrompt"
        @dismiss="hideYouTubeOAuthPrompt"
        @copy="copyYouTubeOAuthCode"
        @open="openExternalUrl"
      />
    </AppTwoColumnLayout>
  </AppPageShell>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppTwoColumnLayout from '@/shared/components/layout/AppTwoColumnLayout.vue'
import SiteConfigEditorDialog from '@/features/settings/components/SiteConfigEditorDialog.vue'
import SiteRuntimeTable from '@/features/settings/components/SiteRuntimeTable.vue'
import YouTubeOAuthPrompt from '@/features/settings/components/YouTubeOAuthPrompt.vue'
import { Button } from '@/shared/ui/button'
import { Input } from '@/shared/ui/input'
import { Logger } from '@/shared/lib/logger'
import { shouldRefreshLoginStatusesAfterCookieImport } from '@/shared/lib/site-runtime-login-status'
import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useSiteCatalog } from '@/features/video/composables/useSites'
import { useYouTubeOAuth } from '@/features/settings/composables/useYouTubeOAuth'
import { useSiteConnectivityCache } from '@/features/settings/composables/useSiteConnectivityCache'
import { useSiteDesktopLogin } from '@/features/settings/composables/useSiteDesktopLogin'
import { useSiteRuntimeStatus } from '@/features/settings/composables/useSiteRuntimeStatus'
import {
  disableSiteRuntime,
  enableSiteRuntime,
  getSiteRuntimes,
  getSupportedSites,
  importAllSiteCookies,
  reloadSiteRuntimes,
  testAllSitesConnectivity,
  testSiteConnectivity,
  testSiteLoginStatus,
} from '@/shared/api'

const loading = ref(false)
const reloading = ref(false)
const siteRuntimes = ref([])
const discoveryErrors = ref([])
const actioning = ref(null)
const isInitialLoading = computed(() => loading.value && !siteRuntimes.value.length)

const testingAll = ref(false)
const supportedSites = ref([])

const { catalog: siteCatalog, loadCatalog, saveCatalog } = useSiteCatalog()

// ponytail: connectivity/login result storage + localStorage persistence lives
// in useSiteConnectivityCache. The cache keys + the login-status merge seam are
// owned there so the view's script reads as state → derived → actions.
const {
  connectivityResults,
  loginStatusResults,
  loginStatusTesting,
  lastTestedAt,
  clearLoginStatusCache,
  saveResultsToCache,
  loadResultsFromCache,
  upsertLoginStatus,
} = useSiteConnectivityCache()

// ponytail: desktop-app site login/session handlers + site-name normalisation
// live in useSiteDesktopLogin. loginStatusTesting/upsert/save are injected
// so the desktop cluster doesn't reach into the cache cluster's internals.
const {
  supportsDesktopLoginSite,
  handleDesktopSiteLogin,
  handleClearDesktopSiteSession,
} = useSiteDesktopLogin({
  loginStatusTesting,
  upsertLoginStatus,
  saveResultsToCache,
})

// ponytail: status/network/login badge text + Tailwind classes + capability
// labels + time formatting live in useSiteRuntimeStatus. Only formatTime is
// needed by the sidebar (last-tested timestamp); the table owns its own badge
// formatters via its own useSiteRuntimeStatus instance.
const { formatTime } = useSiteRuntimeStatus()

const selectedCookiesFile = ref(null)
const cookiesFileName = ref('')
const importingCookies = ref(false)

const editingSite = ref(null)
const siteEditorVisible = ref(false)
const siteEditorSaving = ref(false)
const siteEditorError = ref('')

const siteCatalogMap = computed(() => siteCatalog.value || {})
const searchQuery = ref('')

const enrichedSiteRuntimes = computed(() => {
  const resultsMap = new Map()
  if (connectivityResults.value.length > 0 && connectivityResults.value[0]?.results) {
    connectivityResults.value[0].results.forEach(result => {
      resultsMap.set(result.site_name, result)
    })
  }
  const loginResultMap = loginStatusResults.value || {}
  const loginTestingMap = loginStatusTesting.value || {}

  return (siteRuntimes.value || []).map((runtime) => {
    const primarySite = runtime.sites?.[0] || null
    const siteName = primarySite?.site_name || primarySite?.name || ''
    const siteResult = resultsMap.get(siteName) || {}
    const loginStatus = loginResultMap[siteName]

    return {
      ...runtime,
      capabilities: Array.isArray(runtime.capabilities) ? runtime.capabilities : [],
      sites: Array.isArray(runtime.sites) ? runtime.sites : [],
      primarySite,
      siteName,
      siteAccessible: siteResult.accessible,
      siteTesting: !!siteResult.testing,
      siteLoginStatus: loginStatus,
      siteOAuthStatus: loginStatus?.oauth_status || null,
      siteOAuthAccount: loginStatus?.oauth_account || null,
      siteLoginTesting: !!loginTestingMap[siteName],
      siteSupportsLogin: primarySite?.supports_login_status ?? false,
      siteDesktopLoginSupported: supportsDesktopLoginSite(siteName),
    }
  })
})

const displaySiteRuntimes = computed(() => {
  let list = enrichedSiteRuntimes.value

  if (searchQuery.value.trim()) {
    const keyword = searchQuery.value.trim().toLowerCase()
    list = list.filter(runtime =>
      runtime.display_name?.toLowerCase().includes(keyword) ||
      runtime.runtime_id?.toLowerCase().includes(keyword) ||
      runtime.description?.toLowerCase().includes(keyword) ||
      runtime.siteName?.toLowerCase().includes(keyword)
    )
  }

  return list
})

const siteRuntimeSummary = computed(() => ({
  total: enrichedSiteRuntimes.value.length,
  running: enrichedSiteRuntimes.value.filter(runtime => runtime.enabled && runtime.active_runtime?.state === 'running').length,
  attention: enrichedSiteRuntimes.value.filter((runtime) => {
    if (!runtime.enabled) return true
    if (!runtime.active_runtime) return true
    if (runtime.health?.healthy === false) return true
    return ['failed', 'degraded', 'disabled', 'stopped'].includes(runtime.status)
      || ['failed', 'stopped', 'draining'].includes(runtime.active_runtime?.state)
  }).length,
}))

const connectivitySummary = computed(() => {
  if (connectivityResults.value.length === 0) {
    return { total: 0, accessible: 0, failed: 0, success_rate: 0 }
  }
  return connectivityResults.value[0]?.summary || { total: 0, accessible: 0, failed: 0, success_rate: 0 }
})

const handleCookiesFileChange = (event) => {
  const file = event.target.files?.[0]
  selectedCookiesFile.value = file || null
  cookiesFileName.value = file ? file.name : ''
}

const handleImportAllCookies = async () => {
  if (!selectedCookiesFile.value || importingCookies.value) return
  importingCookies.value = true
  try {
    const data = await importAllSiteCookies(selectedCookiesFile.value)
    if (shouldRefreshLoginStatusesAfterCookieImport(data)) {
      if (supportedSites.value.length === 0) await fetchSupportedSites()
      clearLoginStatusCache()
      await testLoginForAllSupportedSites()
      saveResultsToCache()
    }
  } catch (err) {
    Logger.error('Failed to import cookies', err)
  } finally {
    importingCookies.value = false
  }
}

const handleReload = async () => {
  reloading.value = true
  try {
    await reloadSiteRuntimes()
    await fetchSiteRuntimes()
  } catch {
    // silent — reload failure just leaves the list as-is
  } finally {
    reloading.value = false
  }
}

const handleEnable = async (plugin) => {
  actioning.value = plugin.runtime_id
  try {
    await enableSiteRuntime(plugin.runtime_id)
    await fetchSiteRuntimes()
  } catch {
    // silent — enable failure leaves the row as-is
  } finally {
    actioning.value = null
  }
}

const handleDisable = async (plugin) => {
  actioning.value = plugin.runtime_id
  try {
    await disableSiteRuntime(plugin.runtime_id)
    await fetchSiteRuntimes()
  } catch {
    // silent — disable failure leaves the row as-is
  } finally {
    actioning.value = null
  }
}

const handleTestAll = async () => {
  testingAll.value = true
  try {
    try {
      const data = await testAllSitesConnectivity()
      if (data) {
        connectivityResults.value = [data]
      }
    } catch {
      // connectivity test failure is non-fatal — proceed to login tests
    }
    await testLoginForAllSupportedSites()
    saveResultsToCache()
  } finally {
    testingAll.value = false
  }
}

const handleTestSingleBySite = async (siteName) => {
  if (!siteName) return
  try {
    const data = await testSiteConnectivity(siteName)
    if (!data) return
    if (connectivityResults.value.length === 0) {
      connectivityResults.value = [{ results: [], summary: { total: 0, accessible: 0, failed: 0, success_rate: 0 } }]
    }
    const results = connectivityResults.value[0].results
    const existingIndex = results.findIndex(r => r.site_name === siteName)
    if (existingIndex !== -1) results[existingIndex] = data
    else results.push(data)

    const accessible = results.filter(r => r.accessible).length
    connectivityResults.value[0].summary = {
      total: results.length,
      accessible,
      failed: results.length - accessible,
      success_rate: results.length > 0 ? Math.round((accessible / results.length) * 100) : 0
    }
    saveResultsToCache()
  } catch {
    // silent — single-site connectivity test failure
  }
}

const handleTestLoginBySite = async (siteName) => {
  if (!siteName) return
  loginStatusTesting.value[siteName] = true
  try {
    const bridge = getDesktopBridge()
    if (
      bridge?.isDesktop === true
      && supportsDesktopLoginSite(siteName)
      && typeof bridge.getSiteLoginStatus === 'function'
    ) {
      const result = await bridge.getSiteLoginStatus(siteName)
      if (result) upsertLoginStatus(siteName, result)
      return
    }

    try {
      const data = await testSiteLoginStatus(siteName)
      if (data) upsertLoginStatus(siteName, data)
    } catch (err) {
      upsertLoginStatus(siteName, {
        site_name: siteName,
        logged_in: false,
        message: errorMessage(err, '检测失败'),
        checked_at: new Date().toISOString(),
      })
    }
  } finally {
    loginStatusTesting.value[siteName] = false
    saveResultsToCache()
  }
}

const openSiteEditorByRuntime = (plugin) => {
  const siteName = plugin.siteName
  if (!siteName) return
  const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || {}
  editingSite.value = {
    slug: siteName,
    label: catalogInfo.label || plugin.display_name || siteName,
    enabled: catalogInfo.enabled !== false,
    test_url: catalogInfo.test_url || '',
    domains: catalogInfo.domains || [],
    iconUrl: catalogInfo.icon_url || '',
  }
  siteEditorVisible.value = true
}

const closeSiteEditor = () => {
  siteEditorVisible.value = false
  editingSite.value = null
}

const saveSiteEditor = async ({ slug, sitePayload }) => {
  siteEditorSaving.value = true
  try {
    await saveCatalog({ [slug]: sitePayload })
    siteEditorVisible.value = false
  } catch (error) {
    Logger.error('Failed to save site config', error)
  } finally {
    siteEditorSaving.value = false
  }
}

const fetchSiteRuntimes = async () => {
  loading.value = true
  try {
    const data = await getSiteRuntimes()
    siteRuntimes.value = data?.items || []
    discoveryErrors.value = data?.discovery_errors || []
  } catch {
    // silent — fetch failure leaves the prior list
  } finally {
    loading.value = false
  }
}

const fetchSupportedSites = async () => {
  try {
    const data = await getSupportedSites()
    if (data) supportedSites.value = data.sites || []
  } catch {
    // silent
  }
}

const testLoginForAllSupportedSites = async () => {
  const targets = supportedSites.value.filter(site => site.supports_login_status)
  await Promise.all(targets.map(site => handleTestLoginBySite(site.site_name || site.name)))
}

const openExternalUrl = async (targetUrl) => {
  const url = String(targetUrl || '').trim()
  if (!url) return
  const bridge = getDesktopBridge()
  if (bridge?.isDesktop === true && typeof bridge.openExternal === 'function') {
    await bridge.openExternal(url)
    return
  }
  window.open(url, '_blank')
}

// ponytail: YouTube TV-code OAuth flow (start/revoke, verification-code prompt,
// 3s status poll) lives in useYouTubeOAuth. The login-status upsert, runtime
// refresh, and URL opening are injected so the composable doesn't reach into
// the other clusters. Declared after upsertLoginStatus/fetchSiteRuntimes/
// openExternalUrl so all three consts are past their TDZ at call time.
const {
  youtubeOAuthPrompt,
  hideYouTubeOAuthPrompt,
  copyYouTubeOAuthCode,
  handleStartYouTubeOAuth,
  handleRevokeYouTubeOAuth,
} = useYouTubeOAuth({
  upsertLoginStatus,
  refreshSiteRuntimes: fetchSiteRuntimes,
  openExternalUrl,
})

onMounted(() => {
  fetchSiteRuntimes()
  loadCatalog()
  loadResultsFromCache()
  fetchSupportedSites()
})
</script>
