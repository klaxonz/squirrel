import {createRouter, createWebHistory} from 'vue-router'
import LatestVideos from '../views/LatestVideos.vue'
import Subscribed from '../views/Subscribed.vue'
import Settings from '../views/Settings.vue'
import DownloadTasks from '../views/DownloadTasks.vue'
import VideoTab from "../components/VideoTab.vue";
import History from '../views/History.vue';
import Podcasts from '../views/Podcasts.vue'
import VideoPlay from '../views/VideoPlay.vue'
import Login from "../views/Login.vue";
import Register from "../views/Register.vue";
import { useUser } from '../composables/useUser';


const routes = [
  {
    path: '/videos',
    name: 'LatestVideos',
    component: LatestVideos,
    meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
    children: [
      {
        path: 'all',
        name: 'AllVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      },
      {
        path: 'unread',
        name: 'UnreadVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      },
      {
        path: 'read',
        name: 'ReadVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      },
      {
        path: 'preview',
        name: 'PreviewVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
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
    redirect: {name: 'AllVideos'},
  },
  {
    path: '/',
    redirect: {name: 'AllVideos', replace: true}
  },
  {
    path: '/subscribed',
    name: 'Subscribed',
    component: Subscribed,
    meta: { showSearch: true, search: 'subscribed', searchEvent: 'search:subscribed', searchPlaceholder: '搜索频道...' },
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  },
  {
    path: '/subscription/:id',
    name: 'SubscriptionDetail',
    component: LatestVideos,
    meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
    children: [
      {
        path: '',
        name: 'SubscriptionIndex',
        redirect: to => ({name: 'SubscriptionAllVideos', params: {id: to.params.id}})
      },
      {
        path: 'all',
        name: 'SubscriptionAllVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      }
      ,
      {
        path: 'unread',
        name: 'SubscriptionUnreadVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      },
      {
        path: 'read',
        name: 'SubscriptionReadVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      },
      {
        path: 'preview',
        name: 'SubscriptionPreviewVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      },
      {
        path: 'liked',
        name: 'SubscriptionLikedVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      },
      {
        path: 'later',
        name: 'SubscriptionLaterVideos',
        component: VideoTab,
        meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...' },
      }
    ],
  },
  {
    path: '/downloads',
    name: 'Downloads',
    component: DownloadTasks,
    meta: { showSearch: true, search: 'downloads', searchEvent: 'search:downloads', searchPlaceholder: '搜索下载任务...' },
  },
  {
    path: '/history',
    name: 'History',
    component: History,
    meta: { showSearch: true, search: 'history', searchEvent: 'search:history', searchPlaceholder: '搜索历史记录...' },
  },
  {
    path: '/podcasts',
    name: 'Podcasts',
    component: Podcasts,
    meta: { showSearch: true, search: 'podcasts', searchEvent: 'search:podcasts', searchPlaceholder: '搜索播客...' },
  },
  {
    path: '/video/:videoId',
    name: 'VideoPlay',
    component: VideoPlay,
    meta: { showSearch: true, search: 'home', searchEvent: 'search:home', searchPlaceholder: '搜索视频...', searchRedirectName: 'AllVideos', searchPersistKey: 'LatestVideos', scrollable: true },
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

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const { getCurrentUser, isAuthenticated } = useUser();
  
  // 如果有 token 但没有用户信息，尝试获取用户信息
  if (localStorage.getItem('token') && !isAuthenticated.value) {
    try {
      await getCurrentUser();
    } catch (error) {
      console.error('Failed to get user info:', error);
    }
  }

  // 需要认证但未登录
  if (to.meta.requiresAuth !== false && !isAuthenticated.value) {
    next('/login');
    return;
  }
  
  // 已登录用户访问登录/注册页面
  if ((to.path === '/login' || to.path === '/register') && isAuthenticated.value) {
    next('/');
    return;
  }

  next();
});

export default router
