<template>
  <div class="site-runtime-content">
    <Alert v-if="discoveryErrors.length" variant="error" class="mb-5">
      <AppIcon name="error" class="size-4" />
      <h5 class="mb-1 font-medium leading-none tracking-tight">发现 {{ discoveryErrors.length }} 个站点失败</h5>
      <p class="truncate text-xs">
        {{ discoveryErrors[0].metadata_path }} · {{ discoveryErrors[0].reason }}
      </p>
    </Alert>

    <div v-if="loading" class="site-runtime-loading" aria-label="正在加载站点">
      <AppSkeleton v-for="i in 6" :key="i" height="3.75rem" rounded="var(--radius-md)" shimmer />
    </div>

    <div v-else-if="loadError" class="app-page-empty">
      <AppEmptyState variant="error" title="站点加载失败" :copy="loadError">
        <template #actions>
          <Button size="sm" @click="$emit('retry')">重试</Button>
        </template>
      </AppEmptyState>
    </div>

    <div v-else-if="!runtimes.length" class="app-page-empty">
      <AppEmptyState
        variant="plain"
        icon="cube"
        :title="filtered ? '没有匹配的站点' : '暂无站点'"
        :copy="filtered ? '调整搜索或状态筛选后再试。' : '本地站点发现后会显示在这里。'"
      >
        <template v-if="filtered" #actions>
          <Button size="sm" severity="secondary" @click="$emit('clear-filters')">清空筛选</Button>
        </template>
      </AppEmptyState>
    </div>

    <template v-else>
      <section class="site-runtime-list app-settings-panel" aria-label="站点来源">
        <header class="site-runtime-list__head">
          <div class="site-runtime-list__heading">
            <h2>来源连接</h2>
            <p aria-label="站点状态概览">
              <span>{{ overview.enabled }} / {{ overview.total }} 已启用</span>
              <span v-if="overview.tested">{{ overview.accessible }} / {{ overview.tested }} 网络可用</span>
              <span v-else>网络尚未检测</span>
              <span v-if="overview.loginSupported">{{ overview.connected }} / {{ overview.loginSupported }} 账户已连接</span>
              <span v-if="overview.attention" class="is-alert">{{ overview.attention }} 个需要处理</span>
            </p>
          </div>
          <span v-if="lastTestedAt" class="site-runtime-list__time">
            上次检测 {{ formatTime(lastTestedAt) }}
          </span>
        </header>

        <article
          v-for="runtime in runtimes"
          :key="runtime.runtime_id"
          class="site-runtime-row site-runtime-columns"
        >
          <div class="site-runtime-row__identity">
            <SiteIcon
              v-if="runtime.primarySite"
              :icon-url="runtime.primarySite.icon_url"
              :site="runtime.siteName"
              :label="runtime.primarySite.site_name || runtime.display_name"
              size="lg"
              class="site-runtime-row__icon"
            />
            <div v-else class="site-runtime-row__placeholder">
              <AppIcon name="cube" class="size-4" />
            </div>

            <div class="site-runtime-row__copy">
              <h3>{{ runtime.display_name }}</h3>
              <p>{{ runtimeSubtitle(runtime) }}</p>
            </div>
          </div>

          <div class="site-runtime-row__signals">
            <div class="site-runtime-signal" :data-tone="getNetworkVariant(runtime)">
              <AppSpinner v-if="runtime.siteTesting" size="sm" />
              <span v-else class="site-runtime-signal__dot" aria-hidden="true" />
              <span>网络</span>
              <strong>{{ runtime.siteTesting ? '检测中' : getNetworkText(runtime) }}</strong>
            </div>

            <div
              class="site-runtime-signal"
              :data-tone="supportsLogin(runtime) ? getLoginVariant(runtime) : 'muted'"
            >
              <AppSpinner v-if="runtime.siteLoginTesting" size="sm" />
              <span v-else class="site-runtime-signal__dot" aria-hidden="true" />
              <span>账户</span>
              <strong>
                {{ runtime.siteLoginTesting
                  ? '检测中'
                  : supportsLogin(runtime)
                    ? getLoginText(runtime)
                    : '无需登录' }}
              </strong>
            </div>
          </div>

          <div class="site-runtime-row__capability-cell">
            <span class="site-runtime-row__cell-label">支持能力</span>
            <div v-if="runtime.capabilities.length" class="site-runtime-row__capabilities">
              <span
                v-for="cap in runtime.capabilities.slice(0, 2)"
                :key="cap.name"
                class="site-runtime-row__capability"
                :title="cap.name"
              >
                {{ getCapabilityLabel(cap.name) }}
              </span>
              <span v-if="runtime.capabilities.length > 2" class="site-runtime-row__capability-more">
                +{{ runtime.capabilities.length - 2 }}
              </span>
            </div>
            <span v-else class="site-runtime-row__capability-empty">未声明</span>
          </div>

          <div class="site-runtime-row__actions">
            <Button
              type="button"
              text severity="secondary"
              size="sm"
              class="site-runtime-row__test"
              :disabled="!runtime.siteName || runtime.siteTesting || runtime.siteLoginTesting"
              :title="runtime.siteTesting || runtime.siteLoginTesting ? '正在检测' : `检测 ${runtime.display_name}`"
              :aria-label="runtime.siteTesting || runtime.siteLoginTesting ? `正在检测 ${runtime.display_name}` : `检测 ${runtime.display_name}`"
              @click="$emit('test-runtime', runtime)"
            >
              <AppSpinner v-if="runtime.siteTesting || runtime.siteLoginTesting" size="sm" />
              <AppIcon v-else name="diagnostics" class="h-4 w-4" />
              检测
            </Button>

            <div class="site-runtime-row__enable">
              <span>{{ runtime.enabled ? '已启用' : '已停用' }}</span>
              <AppSpinner v-if="actioning === runtime.runtime_id" size="sm" />
              <Switch
                v-else
                :model-value="runtime.enabled"
                :disabled="actioning === runtime.runtime_id"
                :aria-label="runtime.enabled ? `停用 ${runtime.display_name}` : `启用 ${runtime.display_name}`"
                @update:model-value="(enabled) => $emit(enabled ? 'enable' : 'disable', runtime)"
              />
            </div>

            <AppActionMenu
              :items="runtimeActionItems(runtime)"
              :trigger-label="`${runtime.display_name} 管理操作`"
              button-class="site-runtime-row__menu"
            />
          </div>
        </article>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import AppActionMenu from '@/shared/components/AppActionMenu.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import { Button } from '@/shared/ui/button'
import { Switch } from '@/shared/ui/switch'
import { Alert } from '@/shared/ui/alert'
import { useSiteRuntimeStatus } from '@/features/settings/composables/useSiteRuntimeStatus'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'

const props = defineProps({
  runtimes: { type: Array, default: () => [] },
  allRuntimes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  actioning: { type: [String, null], default: null },
  filtered: { type: Boolean, default: false },
  lastTestedAt: { type: [String, null], default: null },
  discoveryErrors: { type: Array, default: () => [] },
  loadError: { type: String, default: '' },
})

const emit = defineEmits([
  'enable',
  'disable',
  'test-runtime',
  'test-login',
  'desktop-login',
  'clear-desktop-session',
  'start-oauth',
  'revoke-oauth',
  'edit-site',
  'retry',
  'clear-filters',
])

const {
  getNetworkText,
  getNetworkVariant,
  getLoginText,
  getLoginVariant,
  getCapabilityLabel,
  formatTime,
  supportsLogin,
  isConnected,
  needsAttention,
} = useSiteRuntimeStatus()

const { isDesktop: isDesktopEnv } = useDesktopBridge()
const isDesktopApp = computed(() => isDesktopEnv())

const overview = computed(() => {
  const runtimes = props.allRuntimes
  const loginRuntimes = runtimes.filter(supportsLogin)
  return {
    total: runtimes.length,
    enabled: runtimes.filter(runtime => runtime.enabled).length,
    accessible: runtimes.filter(runtime => runtime.siteAccessible === true).length,
    tested: runtimes.filter(runtime => typeof runtime.siteAccessible === 'boolean').length,
    connected: loginRuntimes.filter(isConnected).length,
    loginSupported: loginRuntimes.length,
    attention: runtimes.filter(needsAttention).length,
  }
})

const runtimeSubtitle = runtime => (
  runtime.primarySite?.domains?.[0]
  || runtime.description
  || runtime.runtime_id
)

const runtimeActionItems = runtime => {
  const oauthConnected = runtime.siteOAuthStatus === 'authenticated' || runtime.siteOAuthStatus === 'pending'
  return [
    {
      label: runtime.siteTesting || runtime.siteLoginTesting ? '检测中' : '检测站点',
      appIcon: 'diagnostics',
      loading: runtime.siteTesting || runtime.siteLoginTesting,
      disabled: !runtime.siteName || runtime.siteTesting || runtime.siteLoginTesting,
      command: () => emit('test-runtime', runtime),
    },
    {
      label: '刷新登录状态',
      appIcon: 'security',
      visible: supportsLogin(runtime),
      disabled: runtime.siteLoginTesting,
      command: () => emit('test-login', runtime.siteName),
    },
    {
      label: runtime.siteLoginStatus?.logged_in ? '重新登录桌面会话' : '打开桌面登录',
      appIcon: 'user',
      visible: isDesktopApp.value && runtime.siteDesktopLoginSupported,
      disabled: runtime.siteLoginTesting,
      command: () => emit('desktop-login', runtime.siteName),
    },
    {
      label: '清除桌面会话',
      appIcon: 'logout',
      danger: true,
      visible: isDesktopApp.value && runtime.siteDesktopLoginSupported && runtime.siteLoginStatus?.logged_in,
      command: () => emit('clear-desktop-session', runtime.siteName),
    },
    {
      label: oauthConnected ? '撤销 YouTube 授权' : '授权 YouTube',
      appIcon: oauthConnected ? 'unlink' : 'link',
      visible: runtime.siteName === 'youtube',
      command: () => emit(oauthConnected ? 'revoke-oauth' : 'start-oauth'),
    },
    { separator: true },
    {
      label: '站点配置',
      appIcon: 'settingsPanel',
      command: () => emit('edit-site', runtime),
    },
  ]
}
</script>

<style scoped>
.site-runtime-content {
  width: 100%;
}

.site-runtime-loading {
  display: grid;
  gap: var(--space-2);
}

.site-runtime-list {
  width: 100%;
}

.site-runtime-columns {
  display: grid;
  grid-template-columns: minmax(14rem, 1.15fr) minmax(14rem, 1fr) minmax(11rem, 0.8fr) auto;
  align-items: center;
  gap: var(--space-4);
}

.site-runtime-list__head {
  display: flex;
  min-height: 4.25rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-5);
  border-bottom: 1px solid var(--app-hairline);
  padding: 0.75rem var(--space-4);
}

.site-runtime-list__heading {
  display: grid;
  min-width: 0;
  gap: 0.3rem;
}

.site-runtime-list__heading h2 {
  margin: 0;
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 650;
}

.site-runtime-list__heading p {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 0.25rem 0.5rem;
  margin: 0;
  color: hsl(var(--muted-foreground) / 0.82);
  font-size: 0.6875rem;
}

.site-runtime-list__heading p span + span::before {
  margin-right: 0.5rem;
  color: hsl(var(--muted-foreground) / 0.34);
  content: '·';
}

.site-runtime-list__heading p .is-alert {
  color: hsl(var(--destructive) / 0.88);
}

.site-runtime-list__time {
  flex: none;
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
  font-variant-numeric: tabular-nums;
}

.site-runtime-row {
  min-height: 5.25rem;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0.75rem var(--space-4);
  transition: background-color var(--duration-fast) var(--ease-default);
}

.site-runtime-row:last-child {
  border-bottom: 0;
}

.site-runtime-row:hover,
.site-runtime-row:focus-within {
  background: var(--app-row-hover-bg);
}

.site-runtime-row__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
}

.site-runtime-row__placeholder {
  width: 2.5rem;
  height: 2.5rem;
  flex: 0 0 auto;
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: var(--radius-md);
}

.site-runtime-row__placeholder {
  display: grid;
  place-items: center;
  background: hsl(var(--muted) / 0.45);
  color: hsl(var(--muted-foreground));
}

.site-runtime-row__copy {
  display: grid;
  min-width: 0;
  gap: 0.125rem;
}

.site-runtime-row__copy h3,
.site-runtime-row__copy p {
  overflow: hidden;
  margin: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-row__copy h3 {
  color: hsl(var(--foreground));
  font-size: 0.875rem;
  font-weight: 620;
}

.site-runtime-row__copy p {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  line-height: 1.35;
}

.site-runtime-row__signals {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-4);
}

.site-runtime-signal {
  display: grid;
  min-width: 6.75rem;
  grid-template-columns: auto auto 1fr;
  align-items: center;
  gap: 0.375rem;
}

.site-runtime-signal__dot {
  width: 0.375rem;
  height: 0.375rem;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.42);
}

.site-runtime-signal > span:not(.site-runtime-signal__dot) {
  color: hsl(var(--muted-foreground) / 0.76);
  font-size: 0.6875rem;
}

.site-runtime-signal strong {
  overflow: hidden;
  color: hsl(var(--foreground) / 0.78);
  font-size: 0.75rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-signal[data-tone='success'] .site-runtime-signal__dot {
  background: hsl(var(--success));
}

.site-runtime-signal[data-tone='critical'] .site-runtime-signal__dot {
  background: hsl(var(--destructive) / 0.82);
}

.site-runtime-signal[data-tone='critical'] strong {
  color: hsl(var(--destructive) / 0.86);
}

.site-runtime-row__capabilities {
  display: flex;
  min-width: 0;
  align-items: center;
  overflow: hidden;
  gap: 0.2rem 0.45rem;
  white-space: nowrap;
}

.site-runtime-row__capability-cell {
  display: grid;
  min-width: 0;
  gap: 0.3rem;
}

.site-runtime-row__cell-label {
  color: hsl(var(--muted-foreground) / 0.68);
  font-size: 0.625rem;
  font-weight: 550;
}

.site-runtime-row__capability,
.site-runtime-row__capability-empty {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
}

.site-runtime-row__capability:not(:last-child)::after {
  margin-left: 0.45rem;
  color: hsl(var(--muted-foreground) / 0.38);
  content: '·';
}

.site-runtime-row__capability-more {
  color: hsl(var(--foreground) / 0.62);
  font-size: 0.6875rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.site-runtime-row__actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: var(--space-1);
}

.site-runtime-row__enable {
  display: flex;
  min-width: 5.5rem;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
}

.site-runtime-row__enable > span {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 550;
}

.site-runtime-row__test {
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
}

@media (max-width: 1050px) {
  .site-runtime-columns {
    grid-template-columns: minmax(14rem, 1.1fr) minmax(14rem, 1fr) auto;
  }

  .site-runtime-row__capability-cell {
    display: none;
  }
}

@media (max-width: 760px) {
  .site-runtime-list__time {
    display: none;
  }

  .site-runtime-columns {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .site-runtime-row__signals {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .site-runtime-row {
    transition: none;
  }
}
</style>
