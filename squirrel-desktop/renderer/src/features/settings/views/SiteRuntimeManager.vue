<template>
  <AppPageShell class="site-runtime-page" variant="compact" :fill="false">
    <AppToolbarFrame bordered compact sticky>
      <div class="site-runtime-toolbar">
        <div class="site-runtime-toolbar__actions">
          <Button
            as-child
            variant="ghost"
            size="sm"
            class="site-runtime-file-button"
            :class="{ 'is-active': selectedCookiesFile }"
          >
            <label>
              <input type="file" accept=".txt,.json" class="hidden" @change="handleCookiesFileChange" />
              <AppIcon name="cookie" class="h-4 w-4" />
              <span>{{ cookiesFileName || '选择凭据' }}</span>
            </label>
          </Button>

          <Button
            v-if="selectedCookiesFile"
            size="sm"
            :disabled="importingCookies"
            @click="handleImportAllCookies"
          >
            <AppSpinner v-if="importingCookies" size="sm" />
            <AppIcon v-else name="upload" class="h-4 w-4" />
            导入
          </Button>

          <Button
            variant="ghost"
            size="sm"
            class="site-runtime-toolbar__action"
            :disabled="testingAll"
            @click="handleTestAll"
          >
            <AppSpinner v-if="testingAll" size="sm" />
            <AppIcon v-else name="diagnostics" class="h-4 w-4" />
            全量检测
          </Button>

          <Button
            variant="ghost"
            size="icon-sm"
            class="app-toolbar-control app-toolbar-icon-button"
            :disabled="reloading || loading"
            title="重新加载站点"
            aria-label="重新加载站点"
            @click="handleReload"
          >
            <AppSpinner v-if="reloading" size="sm" />
            <AppIcon v-else name="refresh" class="h-4 w-4" />
          </Button>
        </div>
      </div>
    </AppToolbarFrame>

    <div class="app-page-content app-page-content--media site-runtime-page__content">
      <SiteRuntimeGrid
        :runtimes="displaySiteRuntimes"
        :loading="isInitialLoading"
        :actioning="actioning"
        :search-query="searchQuery"
        :discovery-errors="discoveryErrors"
        :load-error="loadError"
        @enable="handleEnable"
        @disable="handleDisable"
        @test-runtime="handleTestRuntime"
        @test-login="handleTestLoginBySite"
        @desktop-login="handleDesktopSiteLogin"
        @clear-desktop-session="handleClearDesktopSiteSession"
        @start-oauth="handleStartYouTubeOAuth"
        @revoke-oauth="handleRevokeYouTubeOAuth"
        @edit-site="openSiteEditorByRuntime"
        @retry="fetchSiteRuntimes"
        @clear-search="clearRuntimeSearch"
      />
    </div>

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
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppToolbarFrame from '@/shared/components/layout/AppToolbarFrame.vue'
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
import { useUIStore } from '@/shared/stores/ui'
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
const loadError = ref('')
const actioning = ref(null)
const isInitialLoading = computed(() => loading.value && !siteRuntimes.value.length)

const testingAll = ref(false)
const supportedSites = ref([])
const uiStore = useUIStore()

const { catalog: siteCatalog, loadCatalog, saveCatalog } = useSiteCatalog()

// ponytail: connectivity/login result storage + localStorage persistence lives
// in useSiteConnectivityCache. The cache keys + the login-status merge seam are
// owned there so the view's script reads as state → derived → actions.
const {
  connectivityResults,
  loginStatusResults,
  loginStatusTesting,
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

const selectedCookiesFile = ref(null)
const cookiesFileName = ref('')
const importingCookies = ref(false)

const editingSite = ref(null)
const siteEditorVisible = ref(false)
const siteEditorSaving = ref(false)
const siteEditorError = ref('')

const siteCatalogMap = computed(() => siteCatalog.value || {})
const searchQuery = computed(() => uiStore.getSearchQuery('site-runtimes'))

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

const clearRuntimeSearch = () => {
  uiStore.triggerSearch('site-runtimes', '')
}

const fetchSiteRuntimes = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const data = await getSiteRuntimes()
    siteRuntimes.value = data?.items || []
    discoveryErrors.value = data?.discovery_errors || []
    loadError.value = ''
  } catch (error) {
    Logger.error('Failed to load site runtimes', error)
    if (!siteRuntimes.value.length) {
      loadError.value = errorMessage(error, '无法加载站点运行时，请检查后端连接后重试。')
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

<style scoped>
.site-runtime-page {
  --app-page-max-width: 2400px;
}

.site-runtime-toolbar {
  display: flex;
  width: 100%;
  min-width: 0;
  min-height: 2.5rem;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-5);
}

.site-runtime-toolbar__actions {
  display: flex;
  min-width: 0;
  flex: none;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-2);
}

.site-runtime-file-button {
  max-width: 10rem;
  cursor: pointer;
  color: hsl(var(--muted-foreground) / 0.84);
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

.site-runtime-toolbar__action {
  color: hsl(var(--muted-foreground) / 0.84);
}

.site-runtime-page__content {
  padding-top: var(--space-5);
  padding-bottom: var(--space-8);
}

</style>
