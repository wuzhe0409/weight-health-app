import { createRouter, createWebHashHistory } from 'vue-router'

// Lazy-load every view so the initial bundle stays small; each page (and its
// deps like echarts) is fetched on first navigation.
const routes = [
  { path: '/', redirect: '/ai-chat' },
  { path: '/ai-chat', name: 'ai-chat', component: () => import('@/views/AIChat.vue') },
  { path: '/today', name: 'today', component: () => import('@/views/TodayRecord.vue') },
  { path: '/calendar', name: 'calendar', component: () => import('@/views/HistoryCalendar.vue') },
  { path: '/trends', name: 'trends', component: () => import('@/views/Trends.vue') },
  { path: '/day/:date', name: 'day', component: () => import('@/views/DayDetail.vue') },
  { path: '/settings', name: 'settings', component: () => import('@/views/Settings.vue') },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
