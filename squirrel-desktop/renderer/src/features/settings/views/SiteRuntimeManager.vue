<template>
  <AppPageShell class="site-runtime-page" variant="compact" surface="operate" width="table">
    <main class="app-page-content site-runtime-page__content">
      <AppOperatePageHeader
        title="站点"
        :summary="runtimeSummary"
        description="管理内容来源的启用状态、网络连接与账户授权。"
      >
        <template #actions>
          <input
            ref="cookiesFileInput"
            type="file"
            accept=".txt,.json"
            class="hidden"
            @change="handleCookiesFileChange"
          />

          <Button
            type="button"
            severity="secondary" outlined
            size="sm"
            class="site-runtime-file-button"
            :class="{ 'is-active': selectedCookiesFile }"
            :title="cookiesFileName || '导入 Netscape TXT 或 JSON 格式的登录凭据'"
            @click="openCookiesFilePicker"
          >
            <AppIcon name="cookie" class="h-4 w-4" />
            <span>{{ cookiesFileName || '导入凭据' }}</span>
          </Button>

          <Button
            v-if="selectedCookiesFile"
            severity="secondary" outlined
            size="sm"
            :disabled="importingCookies"
            @click="handleImportAllCookies"
          >
            <AppSpinner v-if="importingCookies" size="sm" />
            <AppIcon v-else name="upload" class="h-4 w-4" />
            导入
          </Button>

          <Button
            size="sm"
            class="site-runtime-primary-action"
            :disabled="testingAll"
            :title="hasCachedProbe ? '重新检测全部站点连通与登录' : '一键检测全部站点（首屏也会自动连通探测）'"
            @click="handleTestAll"
          >
            <AppSpinner v-if="testingAll" size="sm" />
            <AppIcon v-else name="diagnostics" class="h-4 w-4" />
            {{ testingAll ? '检测中…' : (hasCachedProbe ? '重新检测全部' : '检测全部') }}
          </Button>
        </template>
      </AppOperatePageHeader>

      <div class="site-runtime-filterbar">
        <AppSectionNav
          :model-value="statusFilter"
          :options="statusFilterOptions"
          aria-label="站点状态"
          @change="statusFilter = $event"
        />
        <span>状态来自最近一次检测与当前桌面会话</span>
      </div>

      <SiteRuntimeGrid
        :runtimes="displaySites"
        :all-runtimes="enrichedSites"
        :loading="isInitialLoading"
        :actioning="actioning"
        :filtered="Boolean(searchQuery.trim()) || statusFilter !== 'all'"
        :last-tested-at="lastTestedAt"
        :load-error="loadError"
        @enable="handleEnable"
        @disable="handleDisable"
        @test-runtime="handleTestRuntime"
        @test-login="handleTestLoginBySite"
        @desktop-login="handleDesktopSiteLogin"
        @clear-desktop-session="handleClearDesktopSiteSession"
        @start-oauth="handleStartYouTubeOAuth"
        @revoke-oauth="handleRevokeYouTubeOAuth"
        @edit-site="openSiteEditorBySite"
        @retry="fetchSites"
        @clear-filters="clearRuntimeFilters"
      />
    </main>

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
  </AppPageShell>
</template>

<script setup>
import { onMounted, ref, computed } from 'vue'
import { errorMessage } from '@/shared/lib/errorMessage'
import AppPageShell from '@/shared/components/layout/AppPageShell.vue'
import AppOperatePageHeader from '@/shared/components/layout/AppOperatePageHeader.vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import { Spinner as AppSpinner } from '@/shared/ui/skeleton'
import AppSectionNav from '@/shared/components/layout/AppSectionNav.vue'
import SiteConfigEditorDialog from '@/features/settings/components/SiteConfigEditorDialog.vue'
import SiteRuntimeGrid from '@/features/settings/components/SiteRuntimeGrid.vue'
import YouTubeOAuthPrompt from '@/features/settings/components/YouTubeOAuthPrompt.vue'
import { Button } from '@/shared/ui/button'
import { Logger } from '@/shared/lib/logger'
import { shouldRefreshLoginStatusesAfterCookieImport } from '@/shared/lib/site-runtime-login-status'
import { getDesktopBridge } from '@/shared/composables/useDesktopBridge'
import { useSiteCatalog } from '@/features/video/composables/useSites'
import { useYouTubeOAuth } from '@/features/settings/composables/useYouTubeOAuth'
import { useSiteConnectivityCache } from '@/features/settings/composables/useSiteConnectivityCache'
import { useSiteDesktopLogin } from '@/features/settings/composables/useSiteDesktopLogin'
import { useSiteRuntimeStatus } from '@/features/settings/composables/useSiteRuntimeStatus'
import { useUIStore } from '@/shared/stores/ui'
import {
  getSites,
  getSupportedSites,
  importAllSiteCookies,
  testAllSitesConnectivity,
  testSiteConnectivity,
  testSiteLoginStatus,
} from '@/shared/api'

const loading = ref(false)
const sites = ref([])
const loadError = ref('')
const actioning = ref(null)
const isInitialLoading = computed(() => loading.value && !sites.value.length)

const testingAll = ref(false)
const supportedSites = ref([])
const uiStore = useUIStore()
const statusFilter = ref('all')

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

/** True once any probe (auto or manual) has written results. */
const hasCachedProbe = computed(
  () => connectivityResults.value.length > 0 || Boolean(lastTestedAt.value),
)

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

const selectedCookiesFile = ref(null)
const cookiesFileName = ref('')
const importingCookies = ref(false)

const editingSite = ref(null)
const siteEditorVisible = ref(false)
const siteEditorSaving = ref(false)
const siteEditorError = ref('')

const siteCatalogMap = computed(() => siteCatalog.value || {})
const searchQuery = computed(() => uiStore.getSearchQuery('site-runtimes'))
const { needsAttention: runtimeNeedsAttention } = useSiteRuntimeStatus()

const enrichedSites = computed(() => {
  const resultsMap = new Map()
  if (connectivityResults.value.length > 0 && connectivityResults.value[0]?.results) {
    connectivityResults.value[0].results.forEach(result => {
      resultsMap.set(result.site_name, result)
    })
  }
  const loginResultMap = loginStatusResults.value || {}
  const loginTestingMap = loginStatusTesting.value || {}

  return (sites.value || []).map((site) => {
    const siteName = site.site_name || site.name || ''
    const siteResult = resultsMap.get(siteName) || {}
    const loginStatus = loginResultMap[siteName]

    return {
      ...site,
      slug: siteName,
      siteName,
      features: Array.isArray(site.features) ? site.features : [],
      siteAccessible: siteResult.accessible,
      siteTesting: !!siteResult.testing,
      siteLoginStatus: loginStatus,
      siteOAuthStatus: loginStatus?.oauth_status || null,
      siteOAuthAccount: loginStatus?.oauth_account || null,
      siteLoginTesting: !!loginTestingMap[siteName],
      siteSupportsLogin: site.supports_login_status ?? false,
      siteDesktopLoginSupported: supportsDesktopLoginSite(siteName),
    }
  })
})

const displaySites = computed(() => {
  let list = enrichedSites.value

  if (searchQuery.value.trim()) {
    const keyword = searchQuery.value.trim().toLowerCase()
    list = list.filter(site =>
      site.label?.toLowerCase().includes(keyword) ||
      site.siteName?.toLowerCase().includes(keyword) ||
      (Array.isArray(site.domains) ? site.domains.join(' ').toLowerCase() : '').includes(keyword)
    )
  }

  if (statusFilter.value === 'enabled') {
    list = list.filter(site => site.enabled)
  } else if (statusFilter.value === 'attention') {
    list = list.filter(runtimeNeedsAttention)
  }

  return list
})

const enabledRuntimeCount = computed(
  () => enrichedSites.value.filter(site => site.enabled).length,
)
const attentionRuntimeCount = computed(
  () => enrichedSites.value.filter(runtimeNeedsAttention).length,
)
const runtimeSummary = computed(
  () => `${enrichedSites.value.length} 个来源`,
)
const statusFilterOptions = computed(() => [
  { value: 'all', label: '全部', badge: enrichedSites.value.length },
  { value: 'enabled', label: '已启用', badge: enabledRuntimeCount.value },
  { value: 'attention', label: '需处理', badge: attentionRuntimeCount.value },
])

const cookiesFileInput = ref(null)
const handleCookiesFileChange = (event) => {
  const file = event.target.files?.[0]
  selectedCookiesFile.value = file || null
  cookiesFileName.value = file ? file.name : ''
}

const openCookiesFilePicker = () => {
  cookiesFileInput.value?.click()
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
    selectedCookiesFile.value = null
    cookiesFileName.value = ''
    if (cookiesFileInput.value) cookiesFileInput.value.value = ''
  } catch (err) {
    Logger.error('Failed to import cookies', err)
  } finally {
    importingCookies.value = false
  }
}

const handleEnable = async (site) => {
  const slug = site?.slug || site?.siteName
  if (!slug) return
  actioning.value = slug
  try {
    await saveCatalog({ [slug.toLowerCase()]: { enabled: true } })
    await fetchSites()
  } catch {
    // silent — enable failure leaves the row as-is
  } finally {
    actioning.value = null
  }
}

const handleDisable = async (site) => {
  const slug = site?.slug || site?.siteName
  if (!slug) return
  actioning.value = slug
  try {
    await saveCatalog({ [slug.toLowerCase()]: { enabled: false } })
    await fetchSites()
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

const handleTestRuntime = async (runtime) => {
  const siteName = runtime?.siteName
  if (!siteName) return

  const checks = [handleTestSingleBySite(siteName)]
  if (
    runtime.siteSupportsLogin
    || runtime.siteDesktopLoginSupported
    || siteName === 'youtube'
  ) {
    checks.push(handleTestLoginBySite(siteName))
  }
  await Promise.allSettled(checks)
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

const openSiteEditorBySite = (site) => {
  const siteName = site?.siteName
  if (!siteName) return
  const catalogInfo = siteCatalogMap.value[siteName?.toLowerCase()] || {}
  editingSite.value = {
    slug: siteName,
    label: catalogInfo.label || site.label || siteName,
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

const clearRuntimeFilters = () => {
  statusFilter.value = 'all'
  uiStore.triggerSearch('site-runtimes', '')
}

const fetchSites = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const data = await getSites()
    sites.value = data?.sites || []
    loadError.value = ''
  } catch (error) {
    Logger.error('Failed to load sites', error)
    if (!sites.value.length) {
      loadError.value = errorMessage(error, '无法加载站点，请检查后端连接后重试。')
    }
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
// the other clusters. Declared after upsertLoginStatus/fetchSites/
// openExternalUrl so all three consts are past their TDZ at call time.
const {
  youtubeOAuthPrompt,
  hideYouTubeOAuthPrompt,
  copyYouTubeOAuthCode,
  handleStartYouTubeOAuth,
  handleRevokeYouTubeOAuth,
} = useYouTubeOAuth({
  upsertLoginStatus,
  refreshSiteRuntimes: fetchSites,
  openExternalUrl,
})

/**
 * On enter, restore cache; if nothing has been tested yet, run a light
 * connectivity probe so rows are not stuck on permanent「未检测」. Full login
 * probes stay behind the explicit「全量检测」CTA (avoid thrash / captcha storms).
 */
const autoProbeConnectivityIfEmpty = async () => {
  if (connectivityResults.value.length > 0 || lastTestedAt.value) return
  if (testingAll.value) return
  testingAll.value = true
  try {
    const data = await testAllSitesConnectivity()
    if (data) {
      connectivityResults.value = [data]
      saveResultsToCache()
    }
  } catch (error) {
    Logger.warn('Auto site connectivity probe failed', error)
  } finally {
    testingAll.value = false
  }
}

onMounted(() => {
  loadResultsFromCache()
  void (async () => {
    await Promise.all([
      fetchSites(),
      loadCatalog(),
      fetchSupportedSites(),
    ])
    await autoProbeConnectivityIfEmpty()
  })()
})
</script>

<style scoped>
.site-runtime-page {
  --app-page-max-width: var(--app-content-table-max);
}

.site-runtime-page__content {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  padding-top: var(--space-7);
  padding-bottom: var(--space-8);
}

.site-runtime-filterbar {
  display: flex;
  min-height: 2.75rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-md);
  background: hsl(var(--card));
  padding: 0.5rem 0.75rem;
}

.site-runtime-filterbar > span {
  color: hsl(var(--muted-foreground));
  font-size: var(--app-text-xs);
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.site-runtime-file-button {
  max-width: 11rem;
  color: hsl(var(--muted-foreground));
}

.site-runtime-file-button.is-active {
  border-color: var(--app-selection-border);
  background: var(--app-selection-bg);
  color: var(--app-selection-fg);
}

.site-runtime-file-button span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-primary-action {
  min-width: 6.5rem;
}

.site-runtime-refresh {
  width: 2rem;
  height: 2rem;
  color: hsl(var(--muted-foreground));
}

@media (max-width: 900px) {
  .site-runtime-filterbar > span {
    display: none;
  }
}

</style>
