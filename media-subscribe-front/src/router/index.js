import { createRouter, createWebHistory } from 'vue-router'
import LatestVideos from '../views/LatestVideos.vue'
import Subscribed from '../views/Subscribed.vue'
import Settings from '../views/Settings.vue'
import DownloadTasks from '../views/DownloadTasks.vue'
import VideoTab from "../components/VideoTab.vue";

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
        meta: { keepAlive: true }
      },
      {
        path: 'unread',
        name: 'UnreadVideos',
        component: VideoTab,
        meta: { keepAlive: true }
      },
      {
        path: 'read',
        name: 'ReadVideos',
        component: VideoTab,
        meta: { keepAlive: true }
      }
    ],
    redirect: { name: 'AllVideos' },
    meta: { keepAlive: true }
  },
  {
    path: '/',
    redirect: { name: 'AllVideos', replace: true }  // 添加 replace: true
  },
  {
    path: '/subscriptions',
    name: 'Subscriptions',
    component: Subscribed
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  },
  {
    path: '/channel/:id',
    name: 'ChannelDetail',
    component: LatestVideos,
    children: [
      {
        path: 'all',
        name: 'ChannelAllVideos',
        component: VideoTab,
        meta: { keepAlive: true }
      },
      {
        path: 'unread',
        name: 'ChannelUnreadVideos',
        component: VideoTab,
        meta: { keepAlive: true }
      },
      {
        path: 'read',
        name: 'ChannelVideos',
        component: VideoTab,
        meta: { keepAlive: true }
      }
    ],
    meta: { keepAlive: true }
  },
  {
    path: '/download-tasks',
    name: 'DownloadTasks',
    component: DownloadTasks
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
