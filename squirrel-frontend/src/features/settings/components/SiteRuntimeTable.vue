<template>
  <div class="app-workbench__content app-table-content site-runtime-content">
    <Alert v-if="discoveryErrors.length" variant="error" class="mb-3 py-2.5">
      <AppIcon name="error" class="h-4 w-4" />
      <AlertTitle>发现 {{ discoveryErrors.length }} 个站点失败</AlertTitle>
      <AlertDescription class="truncate text-xs">{{ discoveryErrors[0].metadata_path }} · {{ discoveryErrors[0].reason }}</AlertDescription>
    </Alert>
    <div class="app-table-shell">
      <div class="app-table-frame">
        <div class="app-table-head site-runtime-grid">
          <div>站点</div>
          <div>状态</div>
          <div>能力</div>
          <div>网络</div>
          <div>登录</div>
          <div class="text-right">操作</div>
        </div>

        <div v-if="loading" class="app-table-loading app-content-stack app-content-stack--dense">
          <AppSkeleton v-for="i in 5" :key="i" height="4rem" rounded="var(--radius-lg)" shimmer />
        </div>

        <div v-else-if="!runtimes.length" class="app-page-empty app-page-empty--compact">
          <AppEmptyState
            variant="plain"
            icon="cube"
            :title="searchQuery ? '没有匹配的站点' : '暂无站点'"
            :copy="searchQuery ? '更换搜索关键词后再试。' : '本地站点发现后会显示在这里。'"
          />
        </div>

        <div v-else class="app-table-body">
          <div
            v-for="runtime in runtimes"
            :key="runtime.runtime_id"
            class="app-table-row site-runtime-grid group"
          >
            <div class="flex min-w-0 items-center gap-3">
              <SiteIcon
                v-if="runtime.primarySite"
                :icon-url="runtime.primarySite.icon_url"
                :label="runtime.primarySite.site_name || runtime.display_name"
                size="md"
                class="rounded-md border border-border/60"
              />
              <div v-else class="app-surface app-surface--subtle flex h-10 w-10 shrink-0 items-center justify-center text-muted-foreground">
                <AppIcon name="cube" class="h-5 w-5" />
              </div>
              <div class="min-w-0">
                <h3 class="truncate text-sm font-semibold text-foreground">{{ runtime.display_name }}</h3>
                <p v-if="runtime.description" class="mt-1 line-clamp-1 text-xs text-muted-foreground">{{ runtime.description }}</p>
              </div>
            </div>

            <div>
              <span class="inline-flex h-7 items-center rounded-md border px-2 text-xs font-medium" :class="getSiteRuntimeStatusClass(runtime)">
                {{ getSiteRuntimeStatusText(runtime) }}
              </span>
            </div>

            <div class="flex min-w-0 flex-wrap gap-1">
              <span
                v-for="cap in runtime.capabilities.slice(0, 3)"
                :key="cap.name"
                class="rounded-md bg-muted px-1.5 py-0.5 text-xs text-muted-foreground"
                :title="cap.name"
              >
                {{ getCapabilityLabel(cap.name) }}
              </span>
              <span v-if="runtime.capabilities.length > 3" class="text-xs text-muted-foreground">
                +{{ runtime.capabilities.length - 3 }}
              </span>
            </div>

            <div class="text-sm text-muted-foreground">
              <span v-if="runtime.siteTesting" class="inline-flex items-center gap-1">
                <AppSpinner size="sm" />
                检测中
              </span>
              <span v-else>{{ getNetworkText(runtime) }}</span>
            </div>

            <div class="text-sm text-muted-foreground">
              <span v-if="runtime.siteLoginTesting" class="inline-flex items-center gap-1">
                <AppSpinner size="sm" />
                检测中
              </span>
              <span v-else>{{ getLoginText(runtime) }}</span>
            </div>

            <div class="flex items-center justify-end gap-1">
              <Button
                variant="ghost"
                size="icon-sm"
                class="text-muted-foreground"
                :disabled="actioning === runtime.runtime_id"
                :title="runtime.enabled ? '停用站点' : '启用站点'"
                @click="$emit(runtime.enabled ? 'disable' : 'enable', runtime)"
              >
                <AppIcon v-if="runtime.enabled" name="pause" class="h-4 w-4" />
                <AppIcon v-else name="play" class="h-4 w-4 fill-current" />
              </Button>
              <Button
                v-if="runtime.siteName"
                variant="ghost"
                size="icon-sm"
                class="text-muted-foreground"
                :disabled="runtime.siteTesting"
                title="连通性测试"
                @click="$emit('test-connectivity', runtime.siteName)"
              >
                <AppIcon name="bolt" class="h-4 w-4" />
              </Button>
              <Button
                v-if="runtime.siteSupportsLogin"
                variant="ghost"
                size="icon-sm"
                class="text-muted-foreground"
                :disabled="runtime.siteLoginTesting"
                title="验证登录状态"
                @click="$emit('test-login', runtime.siteName)"
              >
                <AppIcon name="security" class="h-4 w-4" />
              </Button>
              <DropdownMenu v-if="isDesktopApp && runtime.siteDesktopLoginSupported">
                <DropdownMenuTrigger as-child>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    class="text-muted-foreground"
                    :disabled="runtime.siteLoginTesting"
                    :title="runtime.siteLoginStatus?.logged_in ? '桌面会话已登录' : '桌面会话'"
                  >
                    <AppIcon
                      :name="runtime.siteLoginStatus?.logged_in ? 'statusSuccess' : 'user'"
                      class="h-4 w-4"
                      :class="{ 'text-success': runtime.siteLoginStatus?.logged_in }"
                    />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" class="w-44">
                  <DropdownMenuItem @click="$emit('desktop-login', runtime.siteName)">
                    <AppIcon name="user" class="h-4 w-4" />
                    <span>{{ runtime.siteLoginStatus?.logged_in ? '重新登录' : '打开桌面登录' }}</span>
                  </DropdownMenuItem>
                  <DropdownMenuItem @click="$emit('test-login', runtime.siteName)">
                    <AppIcon name="refresh" class="h-4 w-4" />
                    <span>刷新登录状态</span>
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem
                    :disabled="!runtime.siteLoginStatus?.logged_in"
                    class="text-destructive focus:text-destructive"
                    @click="$emit('clear-desktop-session', runtime.siteName)"
                  >
                    <AppIcon name="logout" class="h-4 w-4" />
                    <span>清除桌面会话</span>
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <Button
                v-if="runtime.siteName === 'youtube'"
                variant="ghost"
                size="icon-sm"
                class="text-muted-foreground"
                title="授权管理"
                @click="$emit(runtime.siteOAuthStatus === 'authenticated' || runtime.siteOAuthStatus === 'pending' ? 'revoke-oauth' : 'start-oauth')"
              >
                <AppIcon v-if="runtime.siteOAuthStatus === 'authenticated'" name="link" class="h-4 w-4" />
                <AppIcon v-else name="unlink" class="h-4 w-4" />
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                class="text-muted-foreground"
                title="站点配置"
                @click="$emit('edit-site', runtime)"
              >
                <AppIcon name="settingsPanel" class="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * The site-runtime data table. Extracted from SiteRuntimeManager.vue (was a
 * ~180-line template block). Pure presentational: receives the enriched
 * runtimes + loading flag, emits coarse-grained actions the owning view wires
 * to its handlers. The status/network/login badge formatters come from the
 * shared useSiteRuntimeStatus composable.
 *
 * JS (not TS) to match the parent view's existing convention — the enriched
 * runtime shape is built dynamically in the view's computed and not worth a
 * shared type declaration yet.
 */
import { computed } from 'vue'
import AppIcon from '@/shared/icons/AppIcon.vue'
import AppSpinner from '@/shared/components/AppSpinner.vue'
import AppSkeleton from '@/shared/components/AppSkeleton.vue'
import AppEmptyState from '@/shared/components/layout/AppEmptyState.vue'
import SiteIcon from '@/shared/components/SiteIcon.vue'
import { Button } from '@/shared/ui/button'
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
  'enable', 'disable',
  'test-connectivity', 'test-login',
  'desktop-login', 'clear-desktop-session',
  'start-oauth', 'revoke-oauth',
  'edit-site',
])

const {
  getSiteRuntimeStatusText,
  getSiteRuntimeStatusClass,
  getNetworkText,
  getLoginText,
  getCapabilityLabel,
} = useSiteRuntimeStatus()

const { isDesktop: isDesktopEnv } = useDesktopBridge()
const isDesktopApp = computed(() => isDesktopEnv())
</script>

<style scoped>
.site-runtime-grid {
  grid-template-columns: var(--app-table-columns);
}

.site-runtime-content {
  --app-table-content-width: 1400px;
  --app-table-min-width: 980px;
  --app-table-columns: minmax(18rem, 1fr) 7rem 12rem 7rem 7rem 15rem;
}

.tabular-nums {
  font-variant-numeric: tabular-nums;
}
</style>
