import { createRouter, createWebHashHistory, type RouteRecordRaw } from 'vue-router'
import { DEFAULT_SETTINGS_TAB, SETTINGS_TABS } from '@/shared/constants/sidebar'
import { useUserStore } from '@/shared/stores/user'
import { useServerConfig } from '@/shared/composables/useServerConfig'
import { Logger } from '@/shared/lib/logger'
import { isApiError } from '@/shared/lib/apiError'
import {
  currentEntry,
  patchCurrentEntryReactive,
  pushEntryReactive,
  replaceEntryReactive,
  resetReactive,
} from '@/shared/lib/navigationHistory'

const HomeView = () => import('@/features/video/views/HomeView.vue')
const VideosView = () => import('@/features/video/views/VideosView.vue')
const ChannelDetailView = () => import('@/features/video/views/ChannelDetailView.vue')
const CreatorDetailView = () => import('@/features/video/views/CreatorDetailView.vue')
const Subscribed = () => import('@/features/video/views/Subscribed.vue')
const RssSources = () => import('@/features/rss/views/RssSources.vue')
const Settings = () => import('@/features/settings/views/Settings.vue')
const VideoTab = () => import('@/features/video/components/feed/VideoTab.vue')
const History = () => import('@/features/video/views/History.vue')
const VideoPlay = () => import('@/features/playback/views/VideoPlay.vue')
const RemoteChannelDetail = () => import('@/features/video/views/RemoteChannelDetail.vue')
const PlaylistView = () => import('@/features/video/views/PlaylistView.vue')
const Music = () => import('@/features/music/views/Music.vue')
const Login = () => import('@/features/auth/views/Login.vue')
const Register = () => import('@/features/auth/views/Register.vue')
const SiteRuntimeManager = () => import('@/features/settings/views/SiteRuntimeManager.vue')
const LogViewer = () => import('@/features/settings/views/LogViewer.vue')
const ScheduledTasks = () => import('@/features/settings/views/ScheduledTasks.vue')
const Profile = () => import('@/features/profile/views/Profile.vue')

const baseSearchMeta = {
  showSearch: true,
  search: 'home',
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

const APP_TITLE = '归仓'

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

const routes: RouteRecordRaw[] = [
  {
    path: '/home',
    name: 'HomeView',
    component: HomeView,
    meta: createSearchMeta('推荐', {
      navKey: 'home',
      sectionLabel: '首页',
      keepAlive: true,
      keepAliveComponent: 'HomeView',
      transitionKey: 'home',
      historyStrategy: 'push',
    }),
  },
  {
    path: '/videos',
    name: 'VideosView',
    component: VideosView,
    meta: createSearchMeta('视频', {
      navKey: 'videos',
      sectionLabel: '视频',
      searchPersistKey: 'VideosView',
      keepAlive: true,
      keepAliveComponent: 'VideosView',
      transitionKey: 'videos',
      historyStrategy: 'push',
    }),
    children: [
      createVideoTabRoute('all', 'AllVideos', '全部视频', { navKey: 'videos', sectionLabel: '视频', historyStrategy: 'replace' }),
      createVideoTabRoute('unread', 'UnreadVideos', '未读视频', { navKey: 'videos', sectionLabel: '视频', historyStrategy: 'replace' }),
      createVideoTabRoute('read', 'ReadVideos', '已读视频', { navKey: 'videos', sectionLabel: '视频', historyStrategy: 'replace' }),
      createVideoTabRoute('preview', 'PreviewVideos', '预览视频', { navKey: 'videos', sectionLabel: '视频', historyStrategy: 'replace' }),
      createVideoTabRoute('liked', 'LikedVideos', '喜欢的视频', { navKey: 'videos', sectionLabel: '视频', historyStrategy: 'replace' }),
      createVideoTabRoute('later', 'LaterVideos', '稍后再看', { navKey: 'videos', sectionLabel: '视频', historyStrategy: 'replace' }),
    ],
    redirect: { name: 'AllVideos' },
  },
  {
    path: '/',
    redirect: { name: 'HomeView', replace: true },
  },
  {
    path: '/subscribed',
    name: 'Subscribed',
    component: Subscribed,
    meta: createSearchMeta('订阅', {
      navKey: 'subscribed',
      sectionLabel: '订阅',
      keepAlive: true,
      keepAliveComponent: 'Subscribed',
      search: 'subscribed',
      searchPlaceholder: '搜索订阅内容或频道',
      historyStrategy: 'push',
    }),
  },
  {
    path: '/rss',
    name: 'RssSources',
    component: RssSources,
    meta: createSearchMeta('RSS 内容源', {
      navKey: 'rss-sources',
      sectionLabel: '内容源',
      search: 'rss',
      searchPlaceholder: '搜索文章',
      searchSuggestions: false,
      historyStrategy: 'push',
      // Collapse the global app rail so the RSS three-pane owns the window.
      sidebar: SidebarMode.fixed,
    }),
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
    redirect: { name: 'SettingsAppearance', replace: true },
    meta: createNoSearchMeta('系统设置', {
      navKey: 'settings',
      sectionLabel: '设置',
      transitionKey: 'settings',
    }),
    children: [
      ...SETTINGS_TABS.map((tab) => ({
        path: tab.path.replace(/^\/settings\/?/, ''),
        name: tab.routeName,
        component: Settings,
        meta: createNoSearchMeta(tab.label, {
          navKey: 'settings',
          sectionLabel: '设置',
          transitionKey: 'settings',
          historyStrategy: 'replace',
        }),
      })),
    ],
  },
  {
    path: '/site-runtimes',
    name: 'SiteRuntimes',
    component: SiteRuntimeManager,
    meta: createSearchMeta('站点', {
      navKey: 'site-runtimes',
      sectionLabel: '站点',
      search: 'site-runtimes',
      searchPlaceholder: '搜索站点或描述',
      searchSuggestions: false,
      historyStrategy: 'push',
    }),
  },
  {
    path: '/logs',
    name: 'Logs',
    component: LogViewer,
    meta: createSearchMeta('日志查看器', {
      navKey: 'logs',
      sectionLabel: '日志',
      search: 'logs',
      searchPlaceholder: '搜索日志内容或追踪编号',
      searchSuggestions: false,
      historyStrategy: 'push',
    }),
  },
  {
    path: '/profile',
    name: 'Profile',
    component: Profile,
    meta: createNoSearchMeta('个人主页', {
      navKey: 'profile',
      sectionLabel: '个人',
      historyStrategy: 'push',
    }),
  },
  {
    path: '/scheduled-tasks',
    name: 'ScheduledTasks',
    component: ScheduledTasks,
    meta: createSearchMeta('计划任务', {
      navKey: 'scheduled-tasks',
      sectionLabel: '定时',
      search: 'scheduled-tasks',
      searchPlaceholder: '搜索任务名称或描述',
      searchSuggestions: false,
      historyStrategy: 'push',
    }),
  },
  {
    path: '/subscription/:id',
    name: 'SubscriptionDetail',
    component: ChannelDetailView,
    meta: createSearchMeta('频道', {
      navKey: 'subscribed',
      sectionLabel: '订阅',
      keepAlive: true,
      keepAliveComponent: 'ChannelDetailView',
      contextParentLabel: '频道',
      transitionKey: 'channel',
      historyStrategy: 'push',
    }),
    children: [
      {
        path: '',
        name: 'SubscriptionIndex',
        redirect: (to) => ({ name: 'SubscriptionAllVideos', params: { id: String(to.params.id) } }),
      },
      createVideoTabRoute('all', 'SubscriptionAllVideos', '全部视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('unread', 'SubscriptionUnreadVideos', '未读视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('read', 'SubscriptionReadVideos', '已读视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('preview', 'SubscriptionPreviewVideos', '预览视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('liked', 'SubscriptionLikedVideos', '喜欢的视频', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('later', 'SubscriptionLaterVideos', '稍后再看', {
        navKey: 'subscribed',
        sectionLabel: '订阅',
        contextParentLabel: '频道',
        historyStrategy: 'replace',
      }),
    ],
  },
  {
    path: '/creator/:id',
    name: 'CreatorDetail',
    component: CreatorDetailView,
    meta: createSearchMeta('创作者', {
      navKey: 'videos',
      sectionLabel: '视频',
      keepAlive: true,
      keepAliveComponent: 'CreatorDetailView',
      contextParentLabel: '创作者',
      transitionKey: 'creator',
      historyStrategy: 'push',
    }),
    children: [
      {
        path: '',
        name: 'CreatorIndex',
        redirect: (to) => ({ name: 'CreatorAllVideos', params: { id: String(to.params.id) } }),
      },
      createVideoTabRoute('all', 'CreatorAllVideos', '全部视频', {
        navKey: 'videos',
        sectionLabel: '视频',
        contextParentLabel: '创作者',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('unread', 'CreatorUnreadVideos', '未读视频', {
        navKey: 'videos',
        sectionLabel: '视频',
        contextParentLabel: '创作者',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('read', 'CreatorReadVideos', '已读视频', {
        navKey: 'videos',
        sectionLabel: '视频',
        contextParentLabel: '创作者',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('preview', 'CreatorPreviewVideos', '预览视频', {
        navKey: 'videos',
        sectionLabel: '视频',
        contextParentLabel: '创作者',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('liked', 'CreatorLikedVideos', '喜欢的视频', {
        navKey: 'videos',
        sectionLabel: '视频',
        contextParentLabel: '创作者',
        historyStrategy: 'replace',
      }),
      createVideoTabRoute('later', 'CreatorLaterVideos', '稍后再看', {
        navKey: 'videos',
        sectionLabel: '视频',
        contextParentLabel: '创作者',
        historyStrategy: 'replace',
      }),
    ],
  },
  {
    path: '/remote-channel',
    name: 'RemoteChannelDetail',
    component: RemoteChannelDetail,
    meta: createNoSearchMeta('远端频道', {
      navKey: 'videos',
      sectionLabel: '视频',
      keepAlive: true,
      keepAliveComponent: 'RemoteChannelDetail',
      scrollable: true,
      hideScrollbar: true,
      historyStrategy: 'push',
    }),
  },
  {
    path: '/history',
    name: 'History',
    component: History,
    meta: createSearchMeta('历史记录', {
      navKey: 'history',
      sectionLabel: '历史',
      search: 'history',
      searchPlaceholder: '搜索历史',
      historyStrategy: 'push',
    }),
  },
  {
    path: '/playlists',
    name: 'Playlists',
    component: PlaylistView,
    meta: createNoSearchMeta('播放列表', {
      navKey: 'playlists',
      sectionLabel: '播放列表',
      historyStrategy: 'push',
    }),
  },
  {
    path: '/music',
    name: 'Music',
    component: Music,
    meta: createSearchMeta('音乐', {
      navKey: 'music',
      sectionLabel: '音乐',
      scrollable: true,
      hideScrollbar: true,
      search: 'music',
      searchPlaceholder: '搜索歌曲、歌手、专辑',
      transitionKey: 'music',
      historyStrategy: 'push',
    }),
  },
  {
    path: '/video/:videoId',
    name: 'VideoPlay',
    component: VideoPlay,
    meta: createNoSearchMeta('视频播放', {
      navKey: 'videos',
      sectionLabel: '视频',
      searchRedirectName: 'AllVideos',
      searchPersistKey: 'VideosView',
      scrollable: true,
      hideScrollbar: true,
      // Watch immersion — no global search header, app rail collapsed.
      sidebar: SidebarMode.fixed,
      transitionKey: 'video',
      historyStrategy: 'push',
    }),
  },
  {
    path: '/server-config',
    name: 'ServerConfig',
    component: () => import('@/features/settings/views/ServerConfig.vue'),
    meta: {
      requiresAuth: false,
      title: '服务器配置',
      layout: 'empty',
      historyStrategy: 'replace',
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
      historyStrategy: 'replace',
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
      historyStrategy: 'replace',
    },
  },
  {
    path: '/settings/:tab',
    redirect: {
      name: SETTINGS_TABS.find((tab) => tab.key === DEFAULT_SETTINGS_TAB)?.routeName || 'SettingsAppearance',
    },
  },
]

// Hash history is required for packaged Electron loads (`file://…/index.html`).
// HTML5 history breaks under the file protocol even with Vite `base: './'`.
const router = createRouter({
  history: createWebHashHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    // 滚动位置完全交给 AppLayout 里的 navigation history entry 决定；
    // 这里只保留"刷新页面回到顶部"的兜底，避免初始加载闪烁。
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
    const user = await userStore.fetchCurrentUser()
    if (user.error && isApiError(user.error) && user.error.status && user.error.status !== 401) {
      Logger.error('Failed to get user info', user.error)
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

// 路由切换后维护应用层 history stack；并同步浏览器标题，
// 让 Electron `page-title-updated` 把标题推到 BrowserWindow（dock 悬停可见）。
//
// 关键点：避免「goBack 触发的 router.replace → afterEach 又 pushEntry」的死循环。
// 通过 useNavigationHistory 写入的「内部跳转」用一个模块级 suppressToken 抑制。
let suppressStackUpdate = 0

export function suppressNextStackUpdate() {
  suppressStackUpdate += 1
}

router.afterEach((to, from) => {
  // 同步窗口标题。Electron 的 page-title-updated 监听器会把新 title 推到 BrowserWindow。
  const pageTitle = String(to.meta?.title ?? APP_TITLE)
  if (typeof document !== 'undefined') {
    document.title = `${pageTitle} - ${APP_TITLE}`
  }

  if (suppressStackUpdate > 0) {
    suppressStackUpdate -= 1
    // 只更新当前 entry 的 fullPath（保证与路由一致），不重新推。
    patchCurrentEntryReactive({
      title: pageTitle,
      scrollY: currentEntry()?.scrollY ?? 0,
    })
    return
  }

  const strategy = (to.meta?.historyStrategy as string) || 'push'
  const fromStrategy = (from.meta?.historyStrategy as string) || 'push'

  // F5 / 深链进入时，sessionStorage 恢复的栈可能已经包含当前 fullPath 的 entry；
  // 这种情况下我们应该 in-place 替换它（保留旧的 scrollY），而不是再 push 一条
  // 把栈变长。
  const existingEntry = currentEntry()
  const reenteringSamePath = existingEntry?.fullPath === to.fullPath

  if (reenteringSamePath) {
    replaceEntryReactive({
      fullPath: to.fullPath,
      name: to.name as string | symbol | null | undefined,
      title: pageTitle,
      breadcrumbs: [],
      sectionLabel: String(to.meta?.sectionLabel ?? ''),
      scrollY: existingEntry?.scrollY ?? 0,
    })
    return
  }

  if (strategy === 'replace') {
    replaceEntryReactive({
      fullPath: to.fullPath,
      name: to.name as string | symbol | null | undefined,
      title: pageTitle,
      breadcrumbs: [],
      sectionLabel: String(to.meta?.sectionLabel ?? ''),
      scrollY: 0,
    })
  } else if (fromStrategy === 'replace' && to.name === from.name) {
    replaceEntryReactive({
      fullPath: to.fullPath,
      name: to.name as string | symbol | null | undefined,
      title: pageTitle,
      breadcrumbs: [],
      sectionLabel: String(to.meta?.sectionLabel ?? ''),
      scrollY: 0,
    })
  } else {
    pushEntryReactive({
      fullPath: to.fullPath,
      name: to.name as string | symbol | null | undefined,
      title: pageTitle,
      breadcrumbs: [],
      sectionLabel: String(to.meta?.sectionLabel ?? ''),
      scrollY: 0,
    })
  }
})

// 登录前清空栈（防止登录后从 /login 跳回首页时栈里残留 /login）
export function resetNavigationStack() {
  resetReactive()
  suppressStackUpdate += 1
}

export default router
