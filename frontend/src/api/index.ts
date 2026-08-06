import axios from 'axios'

const http = axios.create({ baseURL: '/api' })

export const api = {
  parse: (text: string, record_date?: string) =>
    http.post('/records/parse', { text, record_date }),

  saveRecord: (data: any) => http.post('/records', data),

  getRecords: (start?: string, end?: string) =>
    http.get('/records', { params: { start, end } }),

  getRecord: (date: string) => http.get(`/records/${date}`),

  revision: (date: string, data: any) =>
    http.post(`/records/${date}/revisions`, data),

  weightTrend: (start?: string, end?: string) =>
    http.get('/stats/weight-trend', { params: { start, end } }),

  calories: (start?: string, end?: string) =>
    http.get('/stats/calories', { params: { start, end } }),

  cycle: () => http.get('/stats/cycle'),

  searchFood: (keyword: string) =>
    http.get('/stats/search', { params: { keyword } }),

  importHistory: (format = 'json', dry_run = false) =>
    http.post(`/import/history?format=${format}&dry_run=${dry_run}`),

  exportData: (format = 'json') =>
    http.get(`/export?format=${format}`, { responseType: 'blob' }),

  profile: () => http.get('/profile'),

  updateProfile: (data: any) => http.put('/profile', data),

  aiAnalyze: (data: any) => http.post('/ai/analyze', data),

  aiChat: (message: string, history?: any[]) => http.post('/ai/chat', { message, history }),
}

export default api
