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
    children: [
      {
        path: 'all',
        name: 'AllVideos',
        component: VideoTab,
      },
      {
        path: 'unread',
        name: 'UnreadVideos',
        component: VideoTab,
      },
      {
        path: 'read',
        name: 'ReadVideos',
        component: VideoTab,
      },
      {
        path: 'preview',
        name: 'PreviewVideos',
        component: VideoTab,
      },
      {
        path: 'liked',
        name: 'LikedVideos',
        component: VideoTab,
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
    children: [
      {
        path: '',
        redirect: to => ({name: 'SubscriptionAllVideos', params: {id: to.params.id}})
      },
      {
        path: 'all',
        name: 'SubscriptionAllVideos',
        component: VideoTab,
      }
    ],
  },
  {
    path: '/downloads',
    name: 'Downloads',
    component: DownloadTasks
  },
  {
    path: '/history',
    name: 'History',
    component: History,
  },
  {
    path: '/podcasts',
    name: 'Podcasts',
    component: Podcasts
  },
  {
    path: '/video/:videoId',
    name: 'VideoPlay',
    component: VideoPlay
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
