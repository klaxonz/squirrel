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
        height="16rem"
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
              <p>{{ runtime.description || runtime.runtime_id }}</p>
            </div>
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
              <DropdownMenuSeparator
                v-if="supportsLogin(runtime) || (isDesktopApp && runtime.siteDesktopLoginSupported) || runtime.siteName === 'youtube'"
              />
              <DropdownMenuItem @click="$emit('edit-site', runtime)">
                <AppIcon name="settingsPanel" class="h-4 w-4" />
                <span>站点配置</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <div class="site-runtime-card__meta">
          <span class="site-runtime-card__runtime-id">{{ runtime.runtime_id }}</span>
          <span
            class="site-runtime-card__runtime-state"
            :data-tone="getSiteRuntimeStatusVariant(runtime)"
          >
            <span class="site-runtime-card__status-dot" />
            {{ getSiteRuntimeStatusText(runtime) }}
          </span>
        </div>

        <dl class="site-runtime-card__statuses">
          <div class="site-runtime-card__status">
            <dt>运行</dt>
            <dd :data-tone="getSiteRuntimeStatusVariant(runtime)">
              <span class="site-runtime-card__status-dot" />
              {{ runtime.enabled ? '已启用' : '已停用' }}
            </dd>
          </div>
          <div class="site-runtime-card__status">
            <dt>网络</dt>
            <dd :data-tone="getNetworkVariant(runtime)">
              <AppSpinner v-if="runtime.siteTesting" size="sm" />
              <span v-else class="site-runtime-card__status-dot" />
              {{ runtime.siteTesting ? '检测中' : getNetworkText(runtime) }}
            </dd>
          </div>
          <div class="site-runtime-card__status">
            <dt>登录</dt>
            <dd :data-tone="supportsLogin(runtime) ? getLoginVariant(runtime) : 'muted'">
              <AppSpinner v-if="runtime.siteLoginTesting" size="sm" />
              <span v-else class="site-runtime-card__status-dot" />
              {{ runtime.siteLoginTesting
                ? '检测中'
                : supportsLogin(runtime)
                  ? getLoginText(runtime)
                  : '无需登录' }}
            </dd>
          </div>
        </dl>

        <div class="site-runtime-card__capabilities">
          <span class="site-runtime-card__section-label">支持能力</span>
          <div v-if="runtime.capabilities.length" class="site-runtime-card__capability-list">
            <span
              v-for="cap in runtime.capabilities.slice(0, 5)"
              :key="cap.name"
              class="site-runtime-card__capability"
              :title="cap.name"
            >
              {{ getCapabilityLabel(cap.name) }}
            </span>
            <span v-if="runtime.capabilities.length > 5" class="site-runtime-card__capability-more">
              +{{ runtime.capabilities.length - 5 }}
            </span>
          </div>
          <span v-else class="site-runtime-card__capability-empty">未声明能力</span>
        </div>

        <footer class="site-runtime-card__footer">
          <div class="site-runtime-card__enable">
            <AppSpinner v-if="actioning === runtime.runtime_id" size="sm" />
            <span v-else>{{ runtime.enabled ? '已启用' : '已停用' }}</span>
            <Switch
              :model-value="runtime.enabled"
              :disabled="actioning === runtime.runtime_id"
              :aria-label="runtime.enabled ? `停用 ${runtime.display_name}` : `启用 ${runtime.display_name}`"
              @update:model-value="(enabled) => $emit(enabled ? 'enable' : 'disable', runtime)"
            />
          </div>

          <Button
            variant="ghost"
            size="sm"
            class="site-runtime-card__test"
            :disabled="!runtime.siteName || runtime.siteTesting || runtime.siteLoginTesting"
            @click="$emit('test-runtime', runtime)"
          >
            <AppSpinner v-if="runtime.siteTesting || runtime.siteLoginTesting" size="sm" />
            <AppIcon v-else name="sync" class="h-4 w-4" />
            {{ runtime.siteTesting || runtime.siteLoginTesting ? '检测中' : '检测站点' }}
          </Button>
        </footer>
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
  getSiteRuntimeStatusText,
  getSiteRuntimeStatusVariant,
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
  grid-template-columns: repeat(auto-fill, minmax(var(--app-video-grid-min), 1fr));
  gap: var(--app-video-grid-gap);
}

.site-runtime-card {
  display: flex;
  min-width: 0;
  min-height: 16rem;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid hsl(var(--border) / 0.6);
  border-radius: var(--radius-lg);
  background: hsl(var(--card));
  transition:
    border-color var(--duration-fast) var(--ease-default),
    background-color var(--duration-fast) var(--ease-default);
}

.site-runtime-card:hover {
  border-color: hsl(var(--border));
  background: hsl(var(--card) / 0.96);
}

.site-runtime-card__header {
  display: flex;
  min-width: 0;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-4) var(--space-3);
}

.site-runtime-card__identity {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-3);
}

.site-runtime-card__icon,
.site-runtime-card__placeholder {
  width: 2.75rem;
  height: 2.75rem;
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

.site-runtime-card__copy p {
  display: -webkit-box;
  overflow: hidden;
  margin: 0.3rem 0 0;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.75rem;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.site-runtime-card__menu {
  flex: 0 0 auto;
  color: hsl(var(--muted-foreground) / 0.72);
}

.site-runtime-card__meta {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: 0 var(--space-4) var(--space-3);
}

.site-runtime-card__runtime-id {
  overflow: hidden;
  color: hsl(var(--muted-foreground) / 0.56);
  font-family: var(--font-mono);
  font-size: 0.625rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-card__runtime-state {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 0.4rem;
  color: hsl(var(--muted-foreground) / 0.78);
  font-size: 0.6875rem;
  font-weight: 600;
}

.site-runtime-card__status-dot {
  width: 0.4rem;
  height: 0.4rem;
  flex: 0 0 auto;
  border-radius: 999px;
  background: hsl(var(--muted-foreground) / 0.42);
}

[data-tone='active'] > .site-runtime-card__status-dot,
[data-tone='success'] > .site-runtime-card__status-dot {
  background: hsl(var(--success));
}

[data-tone='warning'] > .site-runtime-card__status-dot {
  background: hsl(var(--primary));
}

[data-tone='error'] > .site-runtime-card__status-dot {
  background: hsl(var(--destructive));
}

.site-runtime-card__statuses {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  margin: 0 var(--space-4);
  border-top: 1px solid var(--app-hairline);
  border-bottom: 1px solid var(--app-hairline);
}

.site-runtime-card__status {
  min-width: 0;
  padding: var(--space-3) 0;
}

.site-runtime-card__status + .site-runtime-card__status {
  margin-left: var(--space-3);
  padding-left: var(--space-3);
  border-left: 1px solid var(--app-hairline);
}

.site-runtime-card__status dt {
  color: hsl(var(--muted-foreground) / 0.62);
  font-size: 0.625rem;
  font-weight: 600;
}

.site-runtime-card__status dd {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.4rem;
  overflow: hidden;
  margin: 0.3rem 0 0;
  color: hsl(var(--foreground) / 0.84);
  font-size: 0.75rem;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.site-runtime-card__capabilities {
  display: flex;
  min-height: 5rem;
  flex: 1;
  flex-direction: column;
  gap: var(--space-2);
  padding: var(--space-4);
}

.site-runtime-card__section-label {
  color: hsl(var(--muted-foreground) / 0.62);
  font-size: 0.625rem;
  font-weight: 600;
}

.site-runtime-card__capability-list {
  display: flex;
  min-width: 0;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.site-runtime-card__capability,
.site-runtime-card__capability-more {
  display: inline-flex;
  min-height: 1.45rem;
  align-items: center;
  border-radius: var(--radius-sm);
  padding: 0.125rem 0.4rem;
  background: hsl(var(--accent) / 0.48);
  color: hsl(var(--muted-foreground));
  font-size: 0.6875rem;
  font-weight: 550;
}

.site-runtime-card__capability-more {
  color: hsl(var(--foreground) / 0.68);
  font-variant-numeric: tabular-nums;
}

.site-runtime-card__capability-empty {
  color: hsl(var(--muted-foreground) / 0.64);
  font-size: 0.75rem;
}

.site-runtime-card__footer {
  display: flex;
  min-height: 3.25rem;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  border-top: 1px solid var(--app-hairline);
  padding: 0.625rem var(--space-3) 0.625rem var(--space-4);
}

.site-runtime-card__enable {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: var(--space-2);
  color: hsl(var(--muted-foreground) / 0.72);
  font-size: 0.6875rem;
}

.site-runtime-card__test {
  flex: 0 0 auto;
  color: hsl(var(--muted-foreground) / 0.84);
}

@media (prefers-reduced-motion: reduce) {
  .site-runtime-card {
    transition: none;
  }
}
</style>
