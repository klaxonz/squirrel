import { createRouter, createWebHistory } from 'vue-router'
import { useUser } from '../composables/useUser'
import { Logger } from '@/utils/logger'

const LatestVideos = () => import('../views/LatestVideos.vue')
const Subscribed = () => import('../views/Subscribed.vue')
const Settings = () => import('../views/Settings.vue')
const VideoTab = () => import('@/components/feed/VideoTab.vue')
const History = () => import('../views/History.vue')
const VideoPlay = () => import('../views/VideoPlay.vue')
const Login = () => import('../views/Login.vue')
const Register = () => import('../views/Register.vue')
const PluginManager = () => import('../views/PluginManager.vue')
const LogViewer = () => import('../views/LogViewer.vue')
const ScheduledTasks = () => import('../views/ScheduledTasks.vue')
const SyncCenter = () => import('../views/SyncCenter.vue')

const SEARCH_META = {
  showSearch: true,
  search: 'home',
  searchEvent: 'search:home',
  searchPlaceholder: '搜索'
}

const NO_SEARCH_META = {
  showSearch: false
}

const SIDEBAR_MODE = {
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

const routes = [
  {
    path: '/videos',
    name: 'LatestVideos',
    component: LatestVideos,
    meta: SEARCH_META,
    children: [
      {
        path: 'all',
        name: 'AllVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'unread',
        name: 'UnreadVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'read',
        name: 'ReadVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'preview',
        name: 'PreviewVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'liked',
        name: 'LikedVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home' },
      },
      {
        path: 'later',
        name: 'LaterVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home' },
      }
    ],
    redirect: { name: 'AllVideos' },
  },
  {
    path: '/',
    redirect: {name: 'AllVideos', replace: true}
  },
  {
    path: '/subscribed',
    name: 'Subscribed',
    component: Subscribed,
    meta: {
      showSearch: true,
      search: 'subscribed',
      searchEvent: 'search:subscribed',
      searchPlaceholder: '搜索订阅源'
    },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  },
  {
    path: '/plugins',
    name: 'Plugins',
    component: PluginManager,
    meta: NO_SEARCH_META
  },
  {
    path: '/logs',
    name: 'Logs',
    component: LogViewer,
    meta: NO_SEARCH_META
  },
  {
    path: '/sync-center',
    name: 'SyncCenter',
    component: SyncCenter,
    meta: { showSearch: false, scrollable: true, hideScrollbar: true }
  },
  {
    path: '/scheduled-tasks',
    name: 'ScheduledTasks',
    component: ScheduledTasks,
    meta: NO_SEARCH_META
  },
  {
    path: '/subscription/:id',
    name: 'SubscriptionDetail',
    component: LatestVideos,
    meta: SEARCH_META,
    children: [
      {
        path: '',
        name: 'SubscriptionIndex',
        redirect: (to: any) => ({name: 'SubscriptionAllVideos', params: {id: to.params.id}})
      },
      {
        path: 'all',
        name: 'SubscriptionAllVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'unread',
        name: 'SubscriptionUnreadVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'read',
        name: 'SubscriptionReadVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'preview',
        name: 'SubscriptionPreviewVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'liked',
        name: 'SubscriptionLikedVideos',
        component: VideoTab,
        meta: SEARCH_META,
      },
      {
        path: 'later',
        name: 'SubscriptionLaterVideos',
        component: VideoTab,
        meta: SEARCH_META,
      }
    ],
  },
  {
    path: '/history',
    name: 'History',
    component: History,
    meta: {
      showSearch: true,
      search: 'history',
      searchEvent: 'search:history',
      searchPlaceholder: '搜索历史'
    },
  },
  {
    path: '/video/:videoId',
    name: 'VideoPlay',
    component: VideoPlay,
    meta: {
      showSearch: true,
      search: 'home',
      searchEvent: 'search:home',
      searchPlaceholder: '搜索视频',
      searchRedirectName: 'AllVideos',
      searchPersistKey: 'LatestVideos',
      scrollable: true,
      hideScrollbar: true,
      sidebar: SIDEBAR_MODE.fixed,
    },
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from, next) => {
  const { getCurrentUser, hasResolvedAuth, isAuthenticated } = useUser()

  if (!hasResolvedAuth.value) {
    const result = await getCurrentUser()
    if (result.error?.status && result.error.status !== 401) {
      Logger.error('Failed to get user info', result.error)
    }
  }

  if (to.meta.requiresAuth !== false && !isAuthenticated.value) {
    next('/login')
    return
  }

  if ((to.path === '/login' || to.path === '/register') && isAuthenticated.value) {
    next('/')
    return
  }

  next()
})

export default router
