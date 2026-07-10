<template>
  <div class="site-runtime-grid-content">
    <Alert v-if="discoveryErrors.length" variant="error" class="mb-5">
      <AppIcon name="error" class="h-4 w-4" />
      <AlertTitle>发现 {{ discoveryErrors.length }} 个站点失败</AlertTitle>
      <AlertDescription class="truncate text-xs">
        {{ discoveryErrors[0].metadata_path }} · {{ discoveryErrors[0].reason }}
      </AlertDescription>
    </Alert>

    <div v-if="loading" class="site-runtime-grid" aria-label="正在加载站点">
      <AppSkeleton
        v-for="i in 5"
        :key="i"
        height="13rem"
        rounded="var(--radius-lg)"
        shimmer
      />
    </div>

    <div v-else-if="!runtimes.length" class="app-page-empty">
      <AppEmptyState
        variant="plain"
        icon="cube"
        :title="searchQuery ? '没有匹配的站点' : '暂无站点'"
        :copy="searchQuery ? '更换搜索关键词后再试。' : '本地站点发现后会显示在这里。'"
      />
    </div>

    <div v-else class="site-runtime-grid">
      <article
        v-for="runtime in runtimes"
        :key="runtime.runtime_id"
        class="site-runtime-card"
      >
        <header class="site-runtime-card__header">
          <div class="site-runtime-card__identity">
            <SiteIcon
              v-if="runtime.primarySite"
              :icon-url="runtime.primarySite.icon_url"
              :label="runtime.primarySite.site_name || runtime.display_name"
              size="md"
              class="site-runtime-card__icon"
            />
            <div v-else class="site-runtime-card__placeholder">
              <AppIcon name="cube" class="h-5 w-5" />
            </div>

            <div class="site-runtime-card__copy">
              <h3>{{ runtime.display_name }}</h3>
            </div>
          </div>

          <div class="site-runtime-card__header-actions">
            <div class="site-runtime-card__enable">
              <span>启用</span>
              <AppSpinner v-if="actioning === runtime.runtime_id" size="sm" />
              <Switch
                :model-value="runtime.enabled"
                :disabled="actioning === runtime.runtime_id"
                :aria-label="runtime.enabled ? `停用 ${runtime.display_name}` : `启用 ${runtime.display_name}`"
                @update:model-value="(enabled) => $emit(enabled ? 'enable' : 'disable', runtime)"
              />
            </div>

            <DropdownMenu>
              <DropdownMenuTrigger as-child>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="site-runtime-card__menu"
                  :aria-label="`${runtime.display_name} 管理操作`"
                  title="更多操作"
                >
                  <AppIcon name="more" class="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" class="w-52">
                <DropdownMenuItem
                  :disabled="!runtime.siteName || runtime.siteTesting || runtime.siteLoginTesting"
                  @click="$emit('test-runtime', runtime)"
                >
                  <AppSpinner v-if="runtime.siteTesting || runtime.siteLoginTesting" size="sm" />
                  <AppIcon v-else name="diagnostics" class="h-4 w-4" />
                  <span>
                    {{ runtime.siteTesting || runtime.siteLoginTesting ? '检测中' : '检测站点' }}
                  </span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  v-if="supportsLogin(runtime)"
                  :disabled="runtime.siteLoginTesting"
                  @click="$emit('test-login', runtime.siteName)"
                >
                  <AppIcon name="security" class="h-4 w-4" />
                  <span>刷新登录状态</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  v-if="isDesktopApp && runtime.siteDesktopLoginSupported"
                  :disabled="runtime.siteLoginTesting"
                  @click="$emit('desktop-login', runtime.siteName)"
                >
                  <AppIcon name="user" class="h-4 w-4" />
                  <span>{{ runtime.siteLoginStatus?.logged_in ? '重新登录桌面会话' : '打开桌面登录' }}</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  v-if="isDesktopApp && runtime.siteDesktopLoginSupported && runtime.siteLoginStatus?.logged_in"
                  class="text-destructive focus:text-destructive"
                  @click="$emit('clear-desktop-session', runtime.siteName)"
                >
                  <AppIcon name="logout" class="h-4 w-4" />
                  <span>清除桌面会话</span>
                </DropdownMenuItem>
                <DropdownMenuItem
                  v-if="runtime.siteName === 'youtube'"
                  @click="$emit(runtime.siteOAuthStatus === 'authenticated' || runtime.siteOAuthStatus === 'pending' ? 'revoke-oauth' : 'start-oauth')"
                >
                  <AppIcon
                    :name="runtime.siteOAuthStatus === 'authenticated' ? 'unlink' : 'link'"
                    class="h-4 w-4"
                  />
                  <span>
                    {{ runtime.siteOAuthStatus === 'authenticated' || runtime.siteOAuthStatus === 'pending'
                      ? '撤销 YouTube 授权'
                      : '授权 YouTube' }}
                  </span>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem @click="$emit('edit-site', runtime)">
                  <AppIcon name="settingsPanel" class="h-4 w-4" />
                  <span>站点配置</span>
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </header>

        <dl class="site-runtime-card__statuses" aria-label="站点状态">
          <div class="site-runtime-card__status">
            <dt>网络连通</dt>
            <dd :data-tone="getNetworkVariant(runtime)">
              <AppSpinner v-if="runtime.siteTesting" size="sm" />
              {{ runtime.siteTesting ? '检测中' : getNetworkText(runtime) }}
            </dd>
          </div>
          <div class="site-runtime-card__status">
            <dt>登录状态</dt>
            <dd :data-tone="supportsLogin(runtime) ? getLoginVariant(runtime) : 'muted'">
              <AppSpinner v-if="runtime.siteLoginTesting" size="sm" />
              {{ runtime.siteLoginTesting
                ? '检测中'
                : supportsLogin(runtime)
                  ? getLoginText(runtime)
                  : '无需登录' }}
            </dd>
          </div>
        </dl>

        <div class="site-runtime-card__capabilities">
          <div class="site-runtime-card__section-heading">
            <span class="site-runtime-card__section-label">能力</span>
            <span v-if="runtime.capabilities.length" class="site-runtime-card__capability-count">
              {{ runtime.capabilities.length }} 项
            </span>
          </div>
          <div v-if="runtime.capabilities.length" class="site-runtime-card__capability-list">
            <span
              v-for="cap in runtime.capabilities.slice(0, 4)"
              :key="cap.name"
              class="site-runtime-card__capability"
              :title="cap.name"
            >
              {{ getCapabilityLabel(cap.name) }}
            </span>
            <span v-if="runtime.capabilities.length > 4" class="site-runtime-card__capability-more">
              +{{ runtime.capabilities.length - 4 }}
            </span>
          </div>
          <span v-else class="site-runtime-card__capability-empty">未声明能力</span>
        </div>

      </article>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import { Button } from '@/shared/ui/button'
import { Switch } from '@/shared/ui/switch'
import { Alert, AlertDescription, AlertTitle } from '@/shared/ui/alert'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/shared/ui/dropdown-menu'
import { useSiteRuntimeStatus } from '@/features/settings/composables/useSiteRuntimeStatus'
import { useDesktopBridge } from '@/shared/composables/useDesktopBridge'

defineProps({
  runtimes: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  actioning: { type: [String, null], default: null },
  searchQuery: { type: String, default: '' },
  discoveryErrors: { type: Array, default: () => [] },
})

defineEmits([
  'enable',
  'disable',
  'test-runtime',
  'test-login',
  'desktop-login',
  'clear-desktop-session',
  'start-oauth',
  'revoke-oauth',
  'edit-site',
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
</script>

<style scoped>
.site-runtime-grid-content {
  width: 100%;
}

.site-runtime-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
  gap: var(--space-4);
}

.site-runtime-card {
  display: flex;
  min-width: 0;
  min-height: 13rem;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.58);
  border-radius: var(--radius-lg);
  background: hsl(var(--card) / 0.72);
  transition: border-color var(--duration-fast) var(--ease-default);
}

.site-runtime-card:hover,
.site-runtime-card:focus-within {
  border-color: hsl(var(--border));
}

.site-runtime-card__header {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4);
}

.site-runtime-card__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.site-runtime-card__icon,
.site-runtime-card__placeholder {
  width: 2.5rem;
  height: 2.5rem;
  flex: 0 0 auto;
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: var(--radius-md);
}

.site-runtime-card__placeholder {
  display: grid;
  place-items: center;
  background: hsl(var(--muted) / 0.45);
  color: hsl(var(--muted-foreground));
}

.site-runtime-card__copy {
  min-width: 0;
}

.site-runtime-card__copy h3 {
  overflow: hidden;
  margin: 0;
  color: hsl(var(--foreground) / 0.92);
  font-family: var(--app-heading-font);
  font-size: 1rem;
  font-weight: 650;
  line-height: 1.3;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-card__header-actions {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-1);
}

.site-runtime-card__menu {
  flex: 0 0 auto;
  color: hsl(var(--muted-foreground) / 0.72);
}

.site-runtime-card__status dd[data-tone='critical'] {
  color: hsl(var(--destructive) / 0.82);
}

.site-runtime-card__status dd[data-tone='muted'] {
  color: hsl(var(--muted-foreground) / 0.68);
}

.site-runtime-card__statuses {
  display: flex;
  flex-direction: column;
  margin: 0 var(--space-4);
  border-radius: var(--radius-md);
  padding: 0 var(--space-3);
  background: hsl(var(--muted) / 0.34);
}

.site-runtime-card__status {
  display: flex;
  min-width: 0;
  min-height: 2.25rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.site-runtime-card__status + .site-runtime-card__status {
  border-top: 1px solid hsl(var(--border) / 0.42);
}

.site-runtime-card__status dt {
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.75rem;
  font-weight: 500;
}

.site-runtime-card__status dd {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.4rem;
  overflow: hidden;
  margin: 0;
  color: hsl(var(--muted-foreground) / 0.92);
  font-size: 0.75rem;
  font-weight: 550;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-card__capabilities {
  display: flex;
  min-height: 4.25rem;
  flex: 1;
  flex-direction: column;
  gap: 0.45rem;
  padding: var(--space-3) var(--space-4) var(--space-4);
}

.site-runtime-card__section-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
}

.site-runtime-card__section-label {
  color: hsl(var(--foreground) / 0.72);
  font-size: 0.6875rem;
  font-weight: 600;
}

.site-runtime-card__capability-count {
  color: hsl(var(--muted-foreground) / 0.54);
  font-size: 0.625rem;
  font-variant-numeric: tabular-nums;
}

.site-runtime-card__capability-list {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.2rem 0.45rem;
}

.site-runtime-card__capability {
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  line-height: 1.55;
  white-space: nowrap;
}

.site-runtime-card__capability:not(:last-child)::after {
  margin-left: 0.45rem;
  color: hsl(var(--muted-foreground) / 0.38);
  content: '·';
}

.site-runtime-card__capability-more {
  color: hsl(var(--foreground) / 0.62);
  font-size: 0.6875rem;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.site-runtime-card__capability-empty {
  color: hsl(var(--muted-foreground) / 0.64);
  font-size: 0.6875rem;
}

.site-runtime-card__enable {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
}

@media (prefers-reduced-motion: reduce) {
  .site-runtime-card {
    transition: none;
  }
}
</style>
