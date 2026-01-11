import type { Component } from 'vue'
import {
  HomeIcon,
  BookmarkIcon,
  ClockIcon,
  Cog6ToothIcon as CogIcon,
  PuzzlePieceIcon,
  DocumentTextIcon,
  ChartBarIcon,
  CpuChipIcon,
} from '@heroicons/vue/24/outline'

export interface MenuItem {
  name: string
  path: string
  icon: Component
}

export interface MenuItems {
  main: MenuItem[]
  bottom: MenuItem[]
}

export const MENU_ITEMS: MenuItems = {
  main: [
    {
      name: '首页',
      path: '/',
      icon: HomeIcon,
    },
    {
      name: '订阅',
      path: '/subscribed',
      icon: BookmarkIcon,
    },
    {
      name: '历史',
      path: '/history',
      icon: ClockIcon,
    },
    {
      name: '监控',
      path: '/monitoring',
      icon: ChartBarIcon,
    },
    {
      name: '定时',
      path: '/scheduled-tasks',
      icon: CpuChipIcon,
    },
    {
      name: '插件',
      path: '/plugins',
      icon: PuzzlePieceIcon,
    },
  ],
  bottom: [
    {
      name: '日志',
      path: '/logs',
      icon: DocumentTextIcon,
    },
    {
      name: '设置',
      path: '/settings',
      icon: CogIcon,
    },
  ],
}
