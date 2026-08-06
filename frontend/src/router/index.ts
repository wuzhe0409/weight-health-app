import { createRouter, createWebHashHistory } from 'vue-router'
import TodayRecord from '@/views/TodayRecord.vue'
import AIChat from '@/views/AIChat.vue'
import HistoryCalendar from '@/views/HistoryCalendar.vue'
import Trends from '@/views/Trends.vue'
import DayDetail from '@/views/DayDetail.vue'
import Settings from '@/views/Settings.vue'

const routes = [
  { path: '/', redirect: '/ai-chat' },
  { path: '/ai-chat', name: 'ai-chat', component: AIChat },
  { path: '/today', name: 'today', component: TodayRecord },
  { path: '/calendar', name: 'calendar', component: HistoryCalendar },
  { path: '/trends', name: 'trends', component: Trends },
  { path: '/day/:date', name: 'day', component: DayDetail },
  { path: '/settings', name: 'settings', component: Settings },
]

export default createRouter({
  history: createWebHashHistory(),
  routes,
})
