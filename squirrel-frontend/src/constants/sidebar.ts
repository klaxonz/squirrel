import type { Component } from 'vue'
import {
  ArrowPathIcon,
  BookmarkIcon,
  ChartBarIcon,
  ClockIcon,
  Cog6ToothIcon as CogIcon,
  CpuChipIcon,
  DocumentTextIcon,
  HomeIcon,
  PuzzlePieceIcon,
} from '@heroicons/vue/24/outline'

export interface NavigationItem {
  name: string
  mobileLabel?: string
  path: string
  icon: Component
  group: 'content' | 'operations' | 'system'
  showOnMobile?: boolean
  activePrefixes?: string[]
}

export interface NavigationGroup {
  key: NavigationItem['group']
  label: string
  items: NavigationItem[]
}

export const NAV_ITEMS: NavigationItem[] = [
  {
    name: '首页',
    mobileLabel: '首页',
    path: '/',
    icon: HomeIcon,
    group: 'content',
    showOnMobile: true,
    activePrefixes: ['/videos'],
  },
  {
    name: '订阅',
    mobileLabel: '订阅',
    path: '/subscribed',
    icon: BookmarkIcon,
    group: 'content',
    showOnMobile: true,
    activePrefixes: ['/subscription/'],
  },
  {
    name: '历史',
    mobileLabel: '历史',
    path: '/history',
    icon: ClockIcon,
    group: 'content',
    showOnMobile: true,
  },
  {
    name: '同步中心',
    mobileLabel: '同步',
    path: '/sync-center',
    icon: ArrowPathIcon,
    group: 'operations',
    showOnMobile: true,
  },
  {
    name: '监控',
    mobileLabel: '监控',
    path: '/monitoring',
    icon: ChartBarIcon,
    group: 'operations',
    showOnMobile: true,
  },
  {
    name: '定时',
    mobileLabel: '定时',
    path: '/scheduled-tasks',
    icon: CpuChipIcon,
    group: 'operations',
    showOnMobile: false,
  },
  {
    name: '插件',
    mobileLabel: '插件',
    path: '/plugins',
    icon: PuzzlePieceIcon,
    group: 'system',
    showOnMobile: false,
  },
  {
    name: '日志',
    mobileLabel: '日志',
    path: '/logs',
    icon: DocumentTextIcon,
    group: 'system',
    showOnMobile: true,
  },
  {
    name: '设置',
    mobileLabel: '设置',
    path: '/settings',
    icon: CogIcon,
    group: 'system',
    showOnMobile: true,
  },
]

export const NAV_GROUPS: NavigationGroup[] = [
  {
    key: 'content',
    label: 'Content',
    items: NAV_ITEMS.filter((item) => item.group === 'content'),
  },
  {
    key: 'operations',
    label: 'Operations',
    items: NAV_ITEMS.filter((item) => item.group === 'operations'),
  },
  {
    key: 'system',
    label: 'System',
    items: NAV_ITEMS.filter((item) => item.group === 'system'),
  },
]

export const MOBILE_NAV_ITEMS = NAV_ITEMS.filter((item) => item.showOnMobile)

export function isNavigationItemActive(item: NavigationItem, currentPath: string): boolean {
  if (currentPath === item.path) {
    return true
  }

  return item.activePrefixes?.some((prefix) => currentPath.startsWith(prefix)) ?? false
}
