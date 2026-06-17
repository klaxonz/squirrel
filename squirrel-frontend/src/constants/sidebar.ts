import type {
  RouteLocationNormalizedLoaded,
  RouteLocationRaw,
  RouteRecordName,
} from 'vue-router'
import type { AppIconName } from '@/icons/app-icons'

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

export interface NavigationItem {
  key: AppNavKey
  name: string
  title: string
  path: string
  icon: AppIconName
  group: 'content' | 'operations' | 'system'
  activePrefixes?: string[]
  activeRouteNames?: string[]
}

export interface NavigationGroup {
  key: NavigationItem['group']
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
    group: 'content',
    activeRouteNames: ['HomeView'],
  },
  {
    key: 'videos',
    name: '视频',
    title: '全部视频',
    path: '/videos/all',
    icon: 'film',
    group: 'content',
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
    group: 'content',
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
    group: 'content',
    activeRouteNames: ['RssSources'],
  },
  {
    key: 'music',
    name: '音乐',
    title: '音乐',
    path: '/music',
    icon: 'playlistMusic',
    group: 'content',
    activeRouteNames: ['Music'],
  },
  {
    key: 'history',
    name: '历史',
    title: '历史记录',
    path: '/history',
    icon: 'history',
    group: 'content',
    activeRouteNames: ['History'],
  },
  {
    key: 'playlists',
    name: '播放列表',
    title: '播放列表',
    path: '/playlists',
    icon: 'playlists',
    group: 'content',
    activeRouteNames: ['Playlists'],
  },
  {
    key: 'scheduled-tasks',
    name: '定时',
    title: '计划任务',
    path: '/scheduled-tasks',
    icon: 'scheduledTasks',
    group: 'operations',
    activeRouteNames: ['ScheduledTasks'],
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
  },
]

export const NAV_GROUPS: NavigationGroup[] = [
  {
    key: 'content',
    label: '内容',
    items: NAV_ITEMS.filter((item) => item.group === 'content'),
  },
  {
    key: 'operations',
    label: '运维',
    items: NAV_ITEMS.filter((item) => item.group === 'operations'),
  },
  {
    key: 'system',
    label: '系统',
    items: NAV_ITEMS.filter((item) => item.group === 'system'),
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

  return {
    sectionLabel,
    pageTitle,
    breadcrumbs,
  }
}

