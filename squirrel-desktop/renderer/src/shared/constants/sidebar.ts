import type {
  RouteLocationNormalizedLoaded,
  RouteLocationRaw,
  RouteRecordName,
} from 'vue-router'
import type { AppIconName } from '@/shared/icons/app-icons'

export type AppNavKey =
  | 'home'
  | 'videos'
  | 'subscribed'
  | 'rss-sources'
  | 'history'
  | 'playlists'
  | 'music'
  | 'scheduled-tasks'
  | 'profile'
  | 'site-runtimes'
  | 'logs'
  | 'settings'

export type NavigationGroupKey = 'media' | 'library' | 'system'

export interface NavigationItem {
  key: AppNavKey
  name: string
  title: string
  path: string
  icon: AppIconName
  group: NavigationGroupKey
  activePrefixes?: string[]
  activeRouteNames?: string[]
  /**
   * 解析点击时实际跳转的路径。返回 `null` 时回退到 `path`。
   * 当前仅 settings 用：已在 settings 内时保持当前 tab；否则进入默认 tab。
   */
  resolvePath?: (currentPath: string) => string | null
}

export interface NavigationGroup {
  key: NavigationGroupKey
  label: string
  items: NavigationItem[]
}

export type SettingsTabKey = 'appearance' | 'content' | 'playback' | 'security' | 'system' | 'server'

export interface SettingsTabItem {
  key: SettingsTabKey
  label: string
  path: string
  routeName: string
  icon: AppIconName
  badge?: string
}

export interface BreadcrumbItem {
  label: string
  to?: RouteLocationRaw
}

export interface RouteContextDescriptor {
  sectionLabel: string
  pageTitle: string
  breadcrumbs: BreadcrumbItem[]
  isTopLevel: boolean
  backTarget?: RouteLocationRaw
}

export const DEFAULT_SETTINGS_TAB: SettingsTabKey = 'appearance'

export const SETTINGS_TABS: SettingsTabItem[] = [
  {
    key: 'appearance',
    label: '外观',
    path: '/settings/appearance',
    routeName: 'SettingsAppearance',
    icon: 'appearance',
  },
  {
    key: 'content',
    label: '内容',
    path: '/settings/content',
    routeName: 'SettingsContent',
    icon: 'content',
  },
  {
    key: 'playback',
    label: '播放',
    path: '/settings/playback',
    routeName: 'SettingsPlayback',
    icon: 'playback',
  },
  {
    key: 'security',
    label: '安全',
    path: '/settings/security',
    routeName: 'SettingsSecurity',
    icon: 'security',
  },
  {
    key: 'system',
    label: '系统',
    path: '/settings/system',
    routeName: 'SettingsSystem',
    icon: 'settingsNav',
  },
  {
    key: 'server',
    label: '服务器',
    path: '/settings/server',
    routeName: 'SettingsServer',
    icon: 'server',
  },
]

const SETTINGS_TAB_BY_ROUTE_NAME = new Map(
  SETTINGS_TABS.map((tab) => [tab.routeName, tab]),
)

export const NAV_ITEMS: NavigationItem[] = [
  {
    key: 'home',
    name: '首页',
    title: '推荐',
    path: '/home',
    icon: 'home',
    group: 'media',
    activeRouteNames: ['HomeView'],
  },
  {
    key: 'videos',
    name: '视频',
    title: '全部视频',
    path: '/videos/all',
    icon: 'film',
    group: 'media',
    activePrefixes: ['/videos', '/video/'],
    activeRouteNames: [
      'VideosView',
      'AllVideos',
      'UnreadVideos',
      'ReadVideos',
      'PreviewVideos',
      'LikedVideos',
      'LaterVideos',
      'VideoPlay',
    ],
  },
  {
    key: 'subscribed',
    name: '订阅',
    title: '订阅中心',
    path: '/subscribed',
    icon: 'subscriptions',
    group: 'media',
    activePrefixes: ['/subscribed', '/subscription/'],
    activeRouteNames: [
      'Subscribed',
      'SubscriptionDetail',
      'SubscriptionIndex',
      'SubscriptionAllVideos',
      'SubscriptionUnreadVideos',
      'SubscriptionReadVideos',
      'SubscriptionPreviewVideos',
      'SubscriptionLikedVideos',
      'SubscriptionLaterVideos',
    ],
  },
  {
    key: 'rss-sources',
    name: 'RSS',
    title: 'RSS 内容源',
    path: '/rss',
    icon: 'rss',
    group: 'media',
    activeRouteNames: ['RssSources'],
  },
  {
    key: 'music',
    name: '音乐',
    title: '音乐',
    path: '/music',
    icon: 'playlistMusic',
    group: 'media',
    activeRouteNames: ['Music'],
  },
  {
    key: 'history',
    name: '历史',
    title: '历史记录',
    path: '/history',
    icon: 'history',
    group: 'library',
    activeRouteNames: ['History'],
  },
  {
    key: 'playlists',
    name: '播放列表',
    title: '播放列表',
    path: '/playlists',
    icon: 'playlists',
    group: 'library',
    activeRouteNames: ['Playlists'],
  },
  {
    key: 'site-runtimes',
    name: '站点',
    title: '站点',
    path: '/site-runtimes',
    icon: 'plugins',
    group: 'system',
    activeRouteNames: ['SiteRuntimes'],
  },
  {
    key: 'scheduled-tasks',
    name: '定时',
    title: '计划任务',
    path: '/scheduled-tasks',
    icon: 'scheduledTasks',
    group: 'system',
    activeRouteNames: ['ScheduledTasks'],
  },
  {
    key: 'logs',
    name: '日志',
    title: '日志查看器',
    path: '/logs',
    icon: 'logs',
    group: 'system',
    activeRouteNames: ['Logs'],
  },
  {
    key: 'settings',
    name: '设置',
    title: '系统设置',
    path: SETTINGS_TABS.find((tab) => tab.key === DEFAULT_SETTINGS_TAB)?.path || '/settings/appearance',
    icon: 'settingsNav',
    group: 'system',
    activePrefixes: ['/settings'],
    activeRouteNames: ['Settings', ...SETTINGS_TABS.map((tab) => tab.routeName)],
    // UI-012: already under /settings → keep current tab; otherwise use default path.
    resolvePath: (currentPath) => (currentPath.startsWith('/settings') ? currentPath : null),
  },
]

export const SIDEBAR_TOP_ITEMS = NAV_ITEMS.filter((item) => item.key === 'home')
export const SIDEBAR_FOOTER_ITEMS = NAV_ITEMS.filter((item) => item.key === 'settings')

/**
 * Home sits above grouped content navigation; Settings remains footed.
 * Labels stay product-Chinese; order mirrors FreeTube (Subscriptions-like media
 * first, library second, tools last) without inventing a third shell.
 */
export const NAV_GROUPS: NavigationGroup[] = [
  {
    key: 'media',
    label: '订阅与内容',
    items: NAV_ITEMS.filter((item) => item.group === 'media' && item.key !== 'home'),
  },
  {
    key: 'library',
    label: '资料库',
    items: NAV_ITEMS.filter((item) => item.group === 'library'),
  },
  {
    key: 'system',
    label: '工具',
    items: NAV_ITEMS.filter((item) => item.group === 'system' && item.key !== 'settings'),
  },
]


const normalizeRouteName = (routeName: RouteRecordName | null | undefined): string => {
  return typeof routeName === 'string' ? routeName : ''
}

const normalizeNavKey = (value: unknown): AppNavKey | '' => {
  return typeof value === 'string' ? (value as AppNavKey) : ''
}

export function getSettingsTabByRouteName(routeName: RouteRecordName | null | undefined): SettingsTabItem | undefined {
  return SETTINGS_TAB_BY_ROUTE_NAME.get(normalizeRouteName(routeName))
}

export function isNavigationItemActive(
  item: NavigationItem,
  currentRouteOrPath: RouteLocationNormalizedLoaded | string,
): boolean {
  const currentPath = typeof currentRouteOrPath === 'string'
    ? currentRouteOrPath
    : currentRouteOrPath.path

  if (currentPath === item.path) {
    return true
  }

  if (item.activePrefixes?.some((prefix) => currentPath.startsWith(prefix))) {
    return true
  }

  if (typeof currentRouteOrPath === 'string') {
    return false
  }

  const routeNavKey = normalizeNavKey(currentRouteOrPath.meta?.navKey)
  if (routeNavKey && routeNavKey === item.key) {
    return true
  }

  const routeName = normalizeRouteName(currentRouteOrPath.name)
  return item.activeRouteNames?.includes(routeName) ?? false
}

export function findNavigationItemByKey(key: AppNavKey | '' | null | undefined): NavigationItem | undefined {
  if (!key) {
    return undefined
  }

  return NAV_ITEMS.find((item) => item.key === key)
}

export function resolveRouteContext(route: RouteLocationNormalizedLoaded): RouteContextDescriptor {
  const navKey = normalizeNavKey(route.meta?.navKey)
  const navItem = findNavigationItemByKey(navKey)
  const settingsTab = getSettingsTabByRouteName(route.name)

  const pageTitle = String(
    settingsTab?.label
    || route.meta?.title
    || navItem?.title
    || navItem?.name
    || '工作台',
  )

  // Prefer explicit meta, then nav item name. Keep section distinct from page
  // title when possible so the header can drop redundant double labels.
  const sectionLabel = String(route.meta?.sectionLabel || navItem?.name || '工作台')
  const breadcrumbs: BreadcrumbItem[] = []

  if (navItem) {
    breadcrumbs.push({
      label: navItem.name,
      to: navItem.path,
    })
  }

  const contextParentLabel = String(route.meta?.contextParentLabel || '')
  if (contextParentLabel) {
    breadcrumbs.push({ label: contextParentLabel })
  }

  if (!breadcrumbs.length) {
    breadcrumbs.push({ label: pageTitle })
  } else if (breadcrumbs[breadcrumbs.length - 1]?.label !== pageTitle) {
    breadcrumbs.push({ label: pageTitle })
  }

  if (breadcrumbs.length === 1 && breadcrumbs[0]?.label === navItem?.name) {
    breadcrumbs[0] = { label: pageTitle }
  }

  const backTarget = route.meta?.backTarget as RouteLocationRaw | undefined
  // Top-level = landed on the nav item's own path (e.g. /home, /videos/all).
  // Nested detail routes keep section hierarchy in the header.
  const isTopLevel = Boolean(navItem && route.path === navItem.path)

  return {
    sectionLabel,
    pageTitle,
    breadcrumbs,
    isTopLevel,
    backTarget,
  }
}
