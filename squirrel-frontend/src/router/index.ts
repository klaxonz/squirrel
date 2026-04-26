import { createRouter, createWebHistory } from 'vue-router'
import { DEFAULT_SETTINGS_TAB, SETTINGS_TABS } from '@/constants/sidebar'
import { useUserStore } from '../stores/user'
import { useServerConfig } from '../composables/useServerConfig'
import { Logger } from '@/utils/logger'

const LatestVideos = () => import('../views/LatestVideos.vue')
const Subscribed = () => import('../views/Subscribed.vue')
const Settings = () => import('../views/Settings.vue')
const VideoTab = () => import('@/components/feed/VideoTab.vue')
const History = () => import('../views/History.vue')
const VideoPlay = () => import('../views/VideoPlay.vue')
const PlaylistView = () => import('../views/PlaylistView.vue')
const Login = () => import('../views/Login.vue')
const Register = () => import('../views/Register.vue')
const PluginManager = () => import('../views/PluginManager.vue')
const LogViewer = () => import('../views/LogViewer.vue')
const ScheduledTasks = () => import('../views/ScheduledTasks.vue')
const SyncCenter = () => import('../views/SyncCenter.vue')

const baseSearchMeta = {
  showSearch: true,
  search: 'home',
  searchEvent: 'search:home',
  searchPlaceholder: '搜索',
}

const noSearchMeta = {
  showSearch: false,
}

const SidebarMode = {
  fixed: {
    mode: 'fixed',
    defaultOpen: false,
  },
  flyoutClosed: {
    mode: 'flyout',
    defaultOpen: false,
  },
  flyoutOpen: {
    mode: 'flyout',
    defaultOpen: true,
  },
}

const PUBLIC_ROUTES = ['/login', '/register', '/server-config']

const createSearchMeta = (title: string, overrides = {}) => ({
  ...baseSearchMeta,
  title,
  ...overrides,
})

const createNoSearchMeta = (title: string, overrides = {}) => ({
  ...noSearchMeta,
  title,
  ...overrides,
})

const createVideoTabRoute = (
  path: string,
  name: string,
  title: string,
  overrides = {},
) => ({
  path,
  name,
  component: VideoTab,
  meta: createSearchMeta(title, overrides),
})

const routes = [
  {
    path: '/videos',
    name: 'LatestVideos',
    component: LatestVideos,
    meta: createSearchMeta('首页', { navKey: 'videos', sectionLabel: '首页' }),
    children: [
      createVideoTabRoute('all', 'AllVideos', '全部视频', { navKey: 'videos', sectionLabel: '首页' }),
      createVideoTabRoute('unread', 'UnreadVideos', '未读视频', { navKey: 'videos', sectionLabel: '首页' }),
      createVideoTabRoute('read', 'ReadVideos', '已读视频', { navKey: 'videos', sectionLabel: '首页' }),
      createVideoTabRoute('preview', 'PreviewVideos', '预览视频', { navKey: 'videos', sectionLabel: '首页' }),
      createVideoTabRoute('liked', 'LikedVideos', '喜欢的视频', { navKey: 'videos', sectionLabel: '首页' }),
      createVideoTabRoute('later', 'LaterVideos', '稍后再看', { navKey: 'videos', sectionLabel: '首页' }),
    ],
    redirect: { name: 'AllVideos' },
  },
  {
    path: '/',
    redirect: { name: 'AllVideos', replace: true },
  },
  {
    path: '/subscribed',
    name: 'Subscribed',
    component: Subscribed,
    meta: createSearchMeta('订阅中心', {
      navKey: 'subscribed',
      sectionLabel: '订阅',
      search: 'subscribed',
      searchEvent: 'search:subscribed',
      searchPlaceholder: '搜索订阅源',
    }),
  },
  {
    path: '/settings',
    name: 'Settings',
    redirect: { name: 'SettingsAppearance', replace: true },
    meta: createNoSearchMeta('系统设置', {
      navKey: 'settings',
      sectionLabel: '设置',
    }),
  },
  ...SETTINGS_TABS.map((tab) => ({
    path: tab.path,
    name: tab.routeName,
    component: Settings,
    meta: createNoSearchMeta(tab.label, {
      navKey: 'settings',
      sectionLabel: '设置',
    }),
  })),
  {
    path: '/plugins',
    name: 'Plugins',
    component: PluginManager,
    meta: createNoSearchMeta('插件管理', {
      navKey: 'plugins',
      sectionLabel: '插件',
    }),
  },
  {
    path: '/logs',
    name: 'Logs',
    component: LogViewer,
    meta: createNoSearchMeta('日志查看器', {
      navKey: 'logs',
      sectionLabel: '日志',
    }),
  },
  {
    path: '/sync-center',
    name: 'SyncCenter',
    component: SyncCenter,
    meta: createNoSearchMeta('同步中心', {
      navKey: 'sync-center',
      sectionLabel: '采集',
      scrollable: true,
      hideScrollbar: true,
    }),
  },
  {
    path: '/scheduled-tasks',
    name: 'ScheduledTasks',
    component: ScheduledTasks,
    meta: createNoSearchMeta('计划任务', {
      navKey: 'scheduled-tasks',
      sectionLabel: '定时',
    }),
  },
  {
    path: '/subscription/:id',
    name: 'SubscriptionDetail',
    component: LatestVideos,
    meta: createSearchMeta('频道', {
      navKey: 'subscribed',
      sectionLabel: '订阅',
      contextParentLabel: '频道',
    }),
    children: [
      {
        path: '',
        name: 'SubscriptionIndex',
        redirect: (to: any) => ({ name: 'SubscriptionAllVideos', params: { id: to.params.id } }),
      },
      createVideoTabRoute('all', 'SubscriptionAllVideos', '全部视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
      }),
      createVideoTabRoute('unread', 'SubscriptionUnreadVideos', '未读视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
      }),
      createVideoTabRoute('read', 'SubscriptionReadVideos', '已读视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
      }),
      createVideoTabRoute('preview', 'SubscriptionPreviewVideos', '预览视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
      }),
      createVideoTabRoute('liked', 'SubscriptionLikedVideos', '喜欢的视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
      }),
      createVideoTabRoute('later', 'SubscriptionLaterVideos', '稍后再看', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
      }),
    ],
  },
  {
    path: '/history',
    name: 'History',
    component: History,
    meta: createSearchMeta('历史记录', {
      navKey: 'history',
      sectionLabel: '历史',
      search: 'history',
      searchEvent: 'search:history',
      searchPlaceholder: '搜索历史',
    }),
  },
  {
    path: '/playlists',
    name: 'Playlists',
    component: PlaylistView,
    meta: createNoSearchMeta('播放列表', {
      navKey: 'playlists',
      sectionLabel: '播放列表',
    }),
  },
  {
    path: '/video/:videoId',
    name: 'VideoPlay',
    component: VideoPlay,
    meta: createSearchMeta('视频播放', {
      navKey: 'videos',
      sectionLabel: '首页',
      searchRedirectName: 'AllVideos',
      searchPersistKey: 'LatestVideos',
      scrollable: true,
      hideScrollbar: true,
      sidebar: SidebarMode.fixed,
    }),
  },
  {
    path: '/server-config',
    name: 'ServerConfig',
    component: () => import('../views/ServerConfig.vue'),
    meta: {
      requiresAuth: false,
      title: '服务器配置',
      layout: 'empty',
    },
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: {
      requiresAuth: false,
      title: '登录',
      layout: 'auth',
    },
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: {
      requiresAuth: false,
      title: '注册',
      layout: 'auth',
    },
  },
  {
    path: '/settings/:tab',
    redirect: {
      name: SETTINGS_TABS.find((tab) => tab.key === DEFAULT_SETTINGS_TAB)?.routeName || 'SettingsAppearance',
    },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // Restore scroll on browser back/forward navigation;
    // otherwise reset to top. Combined with history.scrollRestoration = 'manual',
    // savedPosition is null on initial page load, preventing auto-scroll.
    if (savedPosition) return savedPosition
    return { top: 0 }
  },
})

router.beforeEach(async (to, from, next) => {
  const userStore = useUserStore()
  const { getServerUrl, initServerConfig } = useServerConfig()

  await initServerConfig()
  const serverUrl = getServerUrl()

  if (!PUBLIC_ROUTES.includes(to.path)) {
    if (!serverUrl) {
      next('/server-config')
      return
    }
  }

  if (!userStore.hasResolvedAuth) {
    const result = await userStore.fetchCurrentUser()
    if (result.error?.status && result.error.status !== 401) {
      Logger.error('Failed to get user info', result.error)
    }
  }

  if (to.meta.requiresAuth !== false && !userStore.isAuthenticated) {
    next('/login')
    return
  }

  if ((to.path === '/login' || to.path === '/register') && userStore.isAuthenticated) {
    next('/')
    return
  }

  next()
})

export default router
