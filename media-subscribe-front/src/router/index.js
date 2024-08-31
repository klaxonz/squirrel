import { createRouter, createWebHistory } from 'vue-router'
import LatestVideos from '../views/LatestVideos.vue'
import Subscribed from '../views/Subscribed.vue'
import Settings from '../views/Settings.vue'
import ChannelDetail from '../views/ChannelDetail.vue'
import DownloadTasks from '../views/DownloadTasks.vue'

const routes = [
  {
    path: '/',
    name: 'LatestVideos',
    component: LatestVideos,
    meta: { keepAlive: true }
  },
  {
    path: '/subscribed',
    name: 'Subscribed',
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
    component: ChannelDetail,
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