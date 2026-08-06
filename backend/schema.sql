-- Weight Health App schema (SQLite)
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_profile (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  gender TEXT NOT NULL DEFAULT 'female',
  age INTEGER,
  height_cm REAL,
  frame_size TEXT,
  target_weight_kg REAL,
  bmr_formula TEXT DEFAULT 'Mifflin-St Jeor',
  llm_provider TEXT DEFAULT 'openai',
  llm_base_url TEXT,
  llm_api_key TEXT,
  llm_model TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS daily_records (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  record_date TEXT NOT NULL UNIQUE,
  weight_kg REAL,
  bowel_movement TEXT NOT NULL DEFAULT 'unknown',
  period_status TEXT,
  period_day INTEGER,
  period_days_until INTEGER,
  total_kcal_min REAL,
  total_kcal_max REAL,
  total_kcal_confirmed REAL,
  protein_g REAL,
  steps INTEGER,
  water_ml INTEGER,
  analysis TEXT,
  notes TEXT,
  data_status TEXT NOT NULL DEFAULT 'estimated',
  raw_input TEXT,
  source TEXT NOT NULL DEFAULT 'manual_or_ai',
  is_locked INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS food_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  daily_record_id INTEGER NOT NULL,
  meal_type TEXT NOT NULL,
  food_name TEXT NOT NULL,
  quantity_text TEXT,
  quantity_g REAL,
  kcal REAL,
  kcal_min REAL,
  kcal_max REAL,
  kcal_source TEXT NOT NULL DEFAULT 'estimated',
  source_note TEXT,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (daily_record_id) REFERENCES daily_records(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS weight_measurements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  measured_at TEXT NOT NULL,
  weight_kg REAL NOT NULL,
  condition TEXT DEFAULT 'morning_fasted_after_urination',
  daily_record_id INTEGER,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (daily_record_id) REFERENCES daily_records(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_log (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_type TEXT NOT NULL,
  entity_id INTEGER,
  action TEXT NOT NULL,
  before_json TEXT,
  after_json TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_daily_records_date ON daily_records(record_date);
CREATE INDEX IF NOT EXISTS idx_food_entries_daily_record ON food_entries(daily_record_id);
CREATE INDEX IF NOT EXISTS idx_weight_measurements_time ON weight_measurements(measured_at);
