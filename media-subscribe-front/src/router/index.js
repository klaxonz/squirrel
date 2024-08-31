import { createRouter, createWebHistory } from 'vue-router'
import LatestVideos from '../views/LatestVideos.vue'
import Subscribed from '../views/Subscribed.vue'
import Settings from '../views/Settings.vue'

const routes = [
  {
    path: '/',
    name: 'LatestVideos',
    component: LatestVideos
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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router