import type {
  RouteLocationNormalizedLoaded,
  RouteLocationRaw,
  RouteRecordName,
} from 'vue-router'
import type { AppIconName } from '@/icons/app-icons'

export type AppNavKey =
  | 'videos'
  | 'subscribed'
  | 'history'
  | 'playlists'
  | 'sync-center'
  | 'scheduled-tasks'
  | 'plugins'
  | 'logs'
  | 'settings'

export interface NavigationItem {
  key: AppNavKey
  name: string
  title: string
  mobileLabel?: string
  path: string
  icon: AppIconName
  group: 'content' | 'operations' | 'system'
  showOnMobile?: boolean
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
    key: 'videos',
    name: '首页',
    title: '内容总览',
    mobileLabel: '首页',
    path: '/videos/all',
    icon: 'home',
    group: 'content',
    showOnMobile: true,
    activePrefixes: ['/videos', '/video/'],
    activeRouteNames: [
      'LatestVideos',
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
    mobileLabel: '订阅',
    path: '/subscribed',
    icon: 'subscriptions',
    group: 'content',
    showOnMobile: true,
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
    key: 'history',
    name: '历史',
    title: '历史记录',
    mobileLabel: '历史',
    path: '/history',
    icon: 'history',
    group: 'content',
    showOnMobile: true,
    activeRouteNames: ['History'],
  },
  {
    key: 'playlists',
    name: '播放列表',
    title: '播放列表',
    mobileLabel: '播放列表',
    path: '/playlists',
    icon: 'playlists',
    group: 'content',
    showOnMobile: true,
    activeRouteNames: ['Playlists'],
  },
  {
    key: 'sync-center',
    name: '采集',
    title: '同步中心',
    mobileLabel: '采集',
    path: '/sync-center',
    icon: 'sync',
    group: 'operations',
    showOnMobile: true,
    activeRouteNames: ['SyncCenter'],
  },
  {
    key: 'scheduled-tasks',
    name: '定时',
    title: '计划任务',
    mobileLabel: '定时',
    path: '/scheduled-tasks',
    icon: 'scheduledTasks',
    group: 'operations',
    showOnMobile: false,
    activeRouteNames: ['ScheduledTasks'],
  },
  {
    key: 'plugins',
    name: '插件',
    title: '插件管理',
    mobileLabel: '插件',
    path: '/plugins',
    icon: 'plugins',
    group: 'system',
    showOnMobile: false,
    activeRouteNames: ['Plugins'],
  },
  {
    key: 'logs',
    name: '日志',
    title: '日志查看器',
    mobileLabel: '日志',
    path: '/logs',
    icon: 'logs',
    group: 'system',
    showOnMobile: true,
    activeRouteNames: ['Logs'],
  },
  {
    key: 'settings',
    name: '设置',
    title: '系统设置',
    mobileLabel: '设置',
    path: SETTINGS_TABS.find((tab) => tab.key === DEFAULT_SETTINGS_TAB)?.path || '/settings/appearance',
    icon: 'settingsNav',
    group: 'system',
    showOnMobile: true,
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

export const MOBILE_NAV_ITEMS = NAV_ITEMS.filter((item) => item.showOnMobile)

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
