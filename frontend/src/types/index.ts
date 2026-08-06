export interface FoodEntry {
  id?: number
  daily_record_id?: number
  meal_type: string
  food_name: string
  quantity_text?: string | null
  quantity_g?: number | null
  kcal?: number | null
  kcal_min?: number | null
  kcal_max?: number | null
  kcal_source?: string
  source_note?: string | null
  sort_order?: number
}

export interface DailyRecord {
  id: number
  record_date: string
  weight_kg: number | null
  bowel_movement: string
  period_status: string | null
  period_day: number | null
  period_days_until: number | null
  total_kcal_min: number | null
  total_kcal_max: number | null
  total_kcal_confirmed: number | null
  analysis: string | null
  notes: string | null
  data_status: string
  raw_input: string | null
  source: string
  is_locked: number
  food_entries: FoodEntry[]
  weight_measurements?: any[]
}

export interface ParsePreview {
  record_date: string | null
  weight_kg: number | null
  bowel_movement: string | null
  period_status: string | null
  period_day: number | null
  period_days_until: number | null
  meals: Record<string, string[]>
  raw_text: string
  note: string
}

export interface WeightPoint {
  record_date: string
  weight_kg: number
  avg7: number | null
  bowel_movement: string
  period_status: string | null
  is_locked: number
}

export interface CaloriePoint {
  record_date: string
  total_kcal_min: number | null
  total_kcal_max: number | null
  total_kcal_confirmed: number | null
  data_status: string
}

export interface ImportResult {
  inserted: number
  skipped: number
  errors: number
  details: any[]
  dry_run: boolean
  source: string
}

export interface UserProfile {
  id?: number
  gender: string
  age: number | null
  height_cm: number | null
  frame_size: string | null
  target_weight_kg: number | null
  bmr_formula?: string
}
