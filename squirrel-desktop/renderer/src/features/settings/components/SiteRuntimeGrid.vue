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
        :title="searchQuery ? '没有匹配的站点' : '暂无站点'"
        :copy="searchQuery ? '更换搜索关键词后再试。' : '本地站点发现后会显示在这里。'"
      >
        <template v-if="searchQuery" #actions>
          <Button size="sm" severity="secondary" @click="$emit('clear-search')">清空搜索</Button>
        </template>
      </AppEmptyState>
    </div>

    <section v-else class="site-runtime-table app-table-shell" aria-label="站点运行状态">
      <div class="site-runtime-table__frame app-table-frame">
        <header class="site-runtime-table__head site-runtime-columns" aria-hidden="true">
          <span>站点</span>
          <span>网络</span>
          <span>登录</span>
          <span>能力</span>
          <span>启用</span>
          <span />
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
              :label="runtime.primarySite.site_name || runtime.display_name"
              size="md"
              class="site-runtime-row__icon"
            />
            <div v-else class="site-runtime-row__placeholder">
              <AppIcon name="cube" class="size-4" />
            </div>

            <div class="site-runtime-row__copy">
              <h3>{{ runtime.display_name }}</h3>
              <span>{{ runtime.runtime_id }}</span>
            </div>
          </div>

          <div class="site-runtime-row__status" :data-tone="getNetworkVariant(runtime)">
            <AppSpinner v-if="runtime.siteTesting" size="sm" />
            <span>{{ runtime.siteTesting ? '检测中' : getNetworkText(runtime) }}</span>
          </div>

          <div
            class="site-runtime-row__status"
            :data-tone="supportsLogin(runtime) ? getLoginVariant(runtime) : 'muted'"
          >
            <AppSpinner v-if="runtime.siteLoginTesting" size="sm" />
            <span>
              {{ runtime.siteLoginTesting
                ? '检测中'
                : supportsLogin(runtime)
                  ? getLoginText(runtime)
                  : '无需登录' }}
            </span>
          </div>

          <div v-if="runtime.capabilities.length" class="site-runtime-row__capabilities">
            <span
              v-for="cap in runtime.capabilities.slice(0, 3)"
              :key="cap.name"
              class="site-runtime-row__capability"
              :title="cap.name"
            >
              {{ getCapabilityLabel(cap.name) }}
            </span>
            <span v-if="runtime.capabilities.length > 3" class="site-runtime-row__capability-more">
              +{{ runtime.capabilities.length - 3 }}
            </span>
          </div>
          <span v-else class="site-runtime-row__capability-empty">未声明</span>

          <div class="site-runtime-row__enable">
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
        </article>
      </div>
    </section>
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

defineProps({
  runtimes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  actioning: { type: [String, null], default: null },
  searchQuery: { type: String, default: '' },
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
  'clear-search',
])

const {
  getNetworkText,
  getNetworkVariant,
  getLoginText,
  getLoginVariant,
  getCapabilityLabel,
} = useSiteRuntimeStatus()

const { isDesktop: isDesktopEnv } = useDesktopBridge()
const isDesktopApp = computed(() => isDesktopEnv())
const supportsLogin = runtime => Boolean(
  runtime.siteSupportsLogin
  || runtime.siteDesktopLoginSupported
  || runtime.siteName === 'youtube',
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

.site-runtime-table {
  overflow-x: auto;
}

.site-runtime-table__frame {
  min-width: 56rem;
}

.site-runtime-columns {
  display: grid;
  grid-template-columns: minmax(13rem, 1.6fr) minmax(6.5rem, 0.7fr) minmax(7rem, 0.8fr) minmax(12rem, 1.4fr) 4rem 2.25rem;
  align-items: center;
  gap: var(--space-3);
}

.site-runtime-table__head {
  min-height: 2.5rem;
  border-bottom: 1px solid var(--app-hairline);
  padding-inline: var(--space-4);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 600;
}

.site-runtime-row {
  min-height: 4rem;
  border-bottom: 1px solid var(--app-hairline);
  padding: 0.625rem var(--space-4);
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

.site-runtime-row__icon,
.site-runtime-row__placeholder {
  width: 2rem;
  height: 2rem;
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
.site-runtime-row__copy span {
  overflow: hidden;
  margin: 0;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-row__copy h3 {
  color: hsl(var(--foreground));
  font-size: 0.8125rem;
  font-weight: 620;
}

.site-runtime-row__copy span {
  color: hsl(var(--muted-foreground));
  font-family: var(--font-mono);
  font-size: 0.625rem;
}

.site-runtime-row__status {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.375rem;
  color: hsl(var(--muted-foreground));
  font-size: 0.75rem;
  font-weight: 520;
}

.site-runtime-row__status span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-row__status[data-tone='success'] {
  color: hsl(var(--success));
}

.site-runtime-row__status[data-tone='critical'] {
  color: hsl(var(--destructive) / 0.82);
}

.site-runtime-row__status[data-tone='muted'] {
  color: hsl(var(--muted-foreground) / 0.68);
}

.site-runtime-row__capabilities {
  display: flex;
  min-width: 0;
  align-items: center;
  overflow: hidden;
  gap: 0.2rem 0.45rem;
  white-space: nowrap;
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

.site-runtime-row__enable {
  display: flex;
  align-items: center;
}

@media (prefers-reduced-motion: reduce) {
  .site-runtime-row {
    transition: none;
  }
}
</style>
