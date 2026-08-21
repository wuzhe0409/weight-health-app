import axios from 'axios'

// Default 30s guard; AI calls get their own longer budget (backend allows 90s).
const http = axios.create({ baseURL: '/api', timeout: 30_000 })
const AI_TIMEOUT = 150_000

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

  restoreBackup: (formData: FormData) =>
    http.post('/import/backup', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),

  profile: () => http.get('/profile'),

  updateProfile: (data: any) => http.put('/profile', data),

  aiAnalyze: (data: any) => http.post('/ai/analyze', data, { timeout: AI_TIMEOUT }),

  aiChat: (message: string, history?: any[]) => http.post('/ai/chat', { message, history }, { timeout: AI_TIMEOUT }),

  // ── Food Library (V2) ──
  searchFoods: (q: string, category?: string, limit?: number) =>
    http.get('/foods/search', { params: { q, category, limit } }),

  addCustomFood: (data: { name: string; category?: string; calories_per_100g?: number; protein_per_100g?: number; carbs_per_100g?: number; fat_per_100g?: number; common_portion?: string; common_portion_g?: number; common_portion_kcal?: number }) =>
    http.post('/foods', data),

  foodCategories: () => http.get('/foods/categories'),

  // ── Vision Food Recognition (V2) ──
  visionFood: (image: string) => http.post('/ai/vision-food', { image }, { timeout: AI_TIMEOUT }),

  // ── Batch Fill (V2) ──
  batchFill: (items: { record_date: string; weight_kg: number | null; bowel_movement: string; period_status?: string | null; period_day?: number | null; period_days_until?: number | null }[]) =>
    http.post('/records/batch-fill', items),

  batchExists: (dates: string[]) => http.post('/records/exists', dates),
}

export default api
