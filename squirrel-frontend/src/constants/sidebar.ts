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
  section: 'main' | 'bottom'
  showOnMobile?: boolean
  activePrefixes?: string[]
}

export interface MenuItems {
  main: NavigationItem[]
  bottom: NavigationItem[]
}

export const NAV_ITEMS: NavigationItem[] = [
  {
    name: '首页',
    mobileLabel: '首页',
    path: '/',
    icon: HomeIcon,
    section: 'main',
    showOnMobile: true,
    activePrefixes: ['/videos'],
  },
  {
    name: '订阅',
    mobileLabel: '订阅',
    path: '/subscribed',
    icon: BookmarkIcon,
    section: 'main',
    showOnMobile: true,
    activePrefixes: ['/subscription/'],
  },
  {
    name: '历史',
    mobileLabel: '历史',
    path: '/history',
    icon: ClockIcon,
    section: 'main',
    showOnMobile: true,
  },
  {
    name: '同步中心',
    mobileLabel: '同步',
    path: '/sync-center',
    icon: ArrowPathIcon,
    section: 'main',
    showOnMobile: true,
  },
  {
    name: '监控',
    mobileLabel: '监控',
    path: '/monitoring',
    icon: ChartBarIcon,
    section: 'main',
    showOnMobile: true,
  },
  {
    name: '定时',
    mobileLabel: '定时',
    path: '/scheduled-tasks',
    icon: CpuChipIcon,
    section: 'main',
    showOnMobile: false,
  },
  {
    name: '插件',
    mobileLabel: '插件',
    path: '/plugins',
    icon: PuzzlePieceIcon,
    section: 'main',
    showOnMobile: false,
  },
  {
    name: '日志',
    mobileLabel: '日志',
    path: '/logs',
    icon: DocumentTextIcon,
    section: 'bottom',
    showOnMobile: true,
  },
  {
    name: '设置',
    mobileLabel: '设置',
    path: '/settings',
    icon: CogIcon,
    section: 'bottom',
    showOnMobile: true,
  },
]

export const MENU_ITEMS: MenuItems = {
  main: NAV_ITEMS.filter((item) => item.section === 'main'),
  bottom: NAV_ITEMS.filter((item) => item.section === 'bottom'),
}

export const MOBILE_NAV_ITEMS = NAV_ITEMS.filter((item) => item.showOnMobile)

export function isNavigationItemActive(item: NavigationItem, currentPath: string): boolean {
  if (currentPath === item.path) {
    return true
  }

  return item.activePrefixes?.some((prefix) => currentPath.startsWith(prefix)) ?? false
}
