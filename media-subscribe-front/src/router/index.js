import {createRouter, createWebHistory} from 'vue-router'
import LatestVideos from '../views/LatestVideos.vue'
import Subscribed from '../views/Subscribed.vue'
import Settings from '../views/Settings.vue'
import DownloadTasks from '../views/DownloadTasks.vue'
import VideoTab from "../components/VideoTab.vue";
import History from '../views/History.vue';
import Podcasts from '../views/Podcasts.vue'
import VideoPlay from '../views/VideoPlay.vue'

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
    path: '/channel/:id',
    name: 'ChannelDetail',
    component: LatestVideos,
    children: [
      {
        path: '',
        redirect: to => ({name: 'ChannelAllVideos', params: {id: to.params.id}})
      },
      {
        path: 'all',
        name: 'ChannelAllVideos',
        component: VideoTab,
      },
      {
        path: 'unread',
        name: 'ChannelUnreadVideos',
        component: VideoTab,
      },
      {
        path: 'read',
        name: 'ChannelVideos',
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
    path: '/video/:channelId/:videoId',
    name: 'VideoPlay',
    component: VideoPlay
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
