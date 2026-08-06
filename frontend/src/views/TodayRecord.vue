<template>
  <div class="page">
    <h2>今日记录</h2>

    <el-alert
      v-if="existing && existing.is_locked === 1"
      type="warning" :closable="false"
      title="该日期为锁定的历史记录"
      description="保存将作为「修订」追加，原始自然语言内容会被保留，修改写入审计日志。"
      style="margin-bottom:16px"
    />

    <el-card class="section">
      <template #header>
        <div style="display:flex;align-items:center;justify-content:space-between">
          <span class="accent-title">📋 记录表单</span>
          <el-tag v-if="existing" size="small" type="info">已加载</el-tag>
        </div>
      </template>

      <!-- 基本记录 -->
      <el-form :model="form" label-width="110px" style="max-width:640px">
        <el-form-item label="日期">
          <el-date-picker v-model="form.record_date" type="date" value-format="YYYY-MM-DD" @change="loadDate" />
        </el-form-item>
        <el-form-item label="晨起体重(kg)">
          <el-input v-model.number="form.weight_kg" type="number" step="0.01" style="max-width:200px" />
        </el-form-item>
        <el-form-item label="排便">
          <el-select v-model="form.bowel_movement" style="max-width:240px">
            <el-option v-for="b in bowelOptions" :key="b.value" :label="b.label" :value="b.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="生理期状态">
          <el-input v-model="form.period_status" placeholder="如 period_day_3 / pre_period_3_days / post_period" style="max-width:280px" />
          <span class="muted" style="margin-left:8px">第 <el-input-number v-model="form.period_day" :min="0" :controls="false" style="width:60px" /> 天</span>
          <span class="muted" style="margin-left:8px">还有 <el-input-number v-model="form.period_days_until" :min="0" :controls="false" style="width:60px" /> 天</span>
        </el-form-item>
      </el-form>

      <!-- 自然语言解析 -->
      <el-divider content-position="left">自然语言录入</el-divider>
      <el-input v-model="nlText" type="textarea" :rows="3" placeholder="例如：6月18日 体重49.5 没拉粑粑 早餐吃了一个包子 午餐吃了跷脚牛肉 晚餐没吃" />
      <el-button type="primary" style="margin-top:10px" @click="onParse" :disabled="!nlText.trim()">解析</el-button>

      <!-- 饮食明细 -->
      <div v-if="foodList.length">
        <el-divider content-position="left">饮食明细</el-divider>
        <div v-for="mealKey in ['breakfast','lunch','dinner','snack','drink']" :key="mealKey" style="margin-bottom:12px">
          <div class="muted" style="margin-bottom:6px">{{ mealLabels[mealKey] }}</div>
          <div v-for="f in foodsByMeal(mealKey)" :key="f._k" style="display:flex;gap:8px;margin-bottom:6px;align-items:center">
            <el-input v-model="f.food_name" placeholder="食物名称" style="width:260px" />
            <el-input v-model="f.quantity_text" placeholder="数量" style="width:220px" />
            <el-input v-model.number="f.kcal" type="number" placeholder="热量" style="width:100px" />
            <el-select v-model="f.kcal_source" style="width:140px">
              <el-option label="官方" value="official" />
              <el-option label="包装营养表" value="package_label" />
              <el-option label="用户确认" value="user_confirmed" />
              <el-option label="估算" value="estimated" />
            </el-select>
            <el-button text type="danger" @click="removeFood(f._k)">删除</el-button>
          </div>
          <el-button text type="primary" @click="addFood(mealKey)">+ 添加{{ mealLabels[mealKey] }}</el-button>
        </div>
      </div>

      <!-- 合计 -->
      <el-divider content-position="left">当日合计与建议</el-divider>
      <el-form :model="form" label-width="110px" style="max-width:640px">
        <el-form-item label="总热量区间">
          <span v-if="form.total_kcal_min != null && form.total_kcal_max != null">
            <b class="stat-num-purple">{{ form.total_kcal_min }} ~ {{ form.total_kcal_max }}</b> kcal
            <span class="muted" style="margin-left:8px">由 AI 估算 / 历史导入</span>
          </span>
          <span v-else class="muted">尚未估算，请在「AI 顾问」中分析后自动填入</span>
        </el-form-item>
        <el-form-item label="数据状态">
          <el-select v-model="form.data_status" style="max-width:240px">
            <el-option label="已确认" value="confirmed" />
            <el-option label="基本确认" value="mostly_confirmed" />
            <el-option label="部分确认" value="partially_confirmed" />
            <el-option label="估算" value="estimated" />
            <el-option label="不完整" value="incomplete" />
          </el-select>
        </el-form-item>
        <el-form-item label="分析与建议">
          <el-input v-model="form.analysis" type="textarea" :rows="3" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.notes" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <el-button type="success" @click="save">保存记录</el-button>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'
import type { DailyRecord, ParsePreview } from '@/types'

const route = useRoute()
const today = new Date().toISOString().slice(0, 10)
const form = reactive({
  record_date: today,
  weight_kg: null as number | null,
  bowel_movement: 'unknown',
  period_status: '',
  period_day: null as number | null,
  period_days_until: null as number | null,
  total_kcal_min: null as number | null,
  total_kcal_max: null as number | null,
  total_kcal_confirmed: null as number | null,
  analysis: '',
  notes: '',
  data_status: 'estimated',
})
const nlText = ref('')
const preview = ref<ParsePreview | null>(null)
const existing = ref<DailyRecord | null>(null)

interface FoodRow {
  _k: number
  meal_type: string
  food_name: string
  quantity_text: string
  kcal: number | null
  kcal_source: string
}
let keySeq = 1
const foodList = ref<FoodRow[]>([])

const mealLabels: Record<string, string> = {
  breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐', drink: '饮料',
}
const bowelOptions = [
  { label: '已排便', value: 'yes' },
  { label: '未排便', value: 'no' },
  { label: '前一天排便', value: 'previous_day_yes' },
  { label: '前一天未排便', value: 'previous_day_no' },
  { label: '当晚才排便', value: 'no_then_evening_yes' },
  { label: '前一晚排便', value: 'previous_evening_yes' },
  { label: '未知', value: 'unknown' },
]

function foodsByMeal(meal: string) { return foodList.value.filter(f => f.meal_type === meal) }
function addFood(meal: string) { foodList.value.push({ _k: keySeq++, meal_type: meal, food_name: '', quantity_text: '', kcal: null, kcal_source: 'estimated' }) }
function removeFood(k: number) { foodList.value = foodList.value.filter(f => f._k !== k) }

async function onParse() {
  if (!nlText.value.trim()) { ElMessage.warning('请先输入文本'); return }
  const { data } = await api.parse(nlText.value, form.record_date)
  preview.value = data
  if (data.weight_kg != null) form.weight_kg = data.weight_kg
  if (data.bowel_movement) form.bowel_movement = data.bowel_movement
  if (data.period_status) form.period_status = data.period_status
  if (data.period_day != null) form.period_day = data.period_day
  if (data.period_days_until != null) form.period_days_until = data.period_days_until
  const rows: FoodRow[] = []
  for (const [meal, items] of Object.entries(data.meals)) {
    for (const item of items as string[]) {
      rows.push({ _k: keySeq++, meal_type: meal, food_name: item, quantity_text: item, kcal: null, kcal_source: 'estimated' })
    }
  }
  foodList.value = rows
  ElMessage.success('解析完成，请核对后保存')
}

async function loadDate() {
  try {
    const { data } = await api.getRecord(form.record_date)
    existing.value = data
    form.weight_kg = data.weight_kg
    form.bowel_movement = data.bowel_movement
    form.period_status = data.period_status || ''
    form.period_day = data.period_day
    form.period_days_until = data.period_days_until
    form.total_kcal_min = data.total_kcal_min
    form.total_kcal_max = data.total_kcal_max
    form.total_kcal_confirmed = data.total_kcal_confirmed
    form.analysis = data.analysis || ''
    form.notes = data.notes || ''
    form.data_status = data.data_status
    foodList.value = (data.food_entries || []).map((f: any) => ({
      _k: keySeq++, meal_type: f.meal_type, food_name: f.food_name,
      quantity_text: f.quantity_text || '', kcal: f.kcal ?? null, kcal_source: f.kcal_source || 'estimated',
    }))
  } catch (e: any) {
    existing.value = null
    if (e.response && e.response.status !== 404) console.error(e)
  }
}

async function save() {
  const payload = {
    record_date: form.record_date,
    weight_kg: form.weight_kg,
    bowel_movement: form.bowel_movement,
    period_status: form.period_status || null,
    period_day: form.period_day,
    period_days_until: form.period_days_until,
    total_kcal_min: form.total_kcal_min,
    total_kcal_max: form.total_kcal_max,
    total_kcal_confirmed: form.total_kcal_confirmed,
    analysis: form.analysis,
    notes: form.notes,
    data_status: form.data_status,
    raw_input: nlText.value || null,
    food_entries: foodList.value.map(f => ({
      meal_type: f.meal_type, food_name: f.food_name, quantity_text: f.quantity_text,
      kcal: f.kcal, kcal_source: f.kcal_source,
    })),
  }
  if (existing.value && existing.value.is_locked === 1) {
    await api.revision(form.record_date, payload)
    ElMessage.success('已作为修订保存（原内容保留，已记录审计）')
  } else {
    await api.saveRecord(payload)
    ElMessage.success('已保存')
  }
  await loadDate()
}

watch(() => route.query.date, (d) => { if (d) form.record_date = String(d); loadDate() })
onMounted(() => {
  if (route.query.date) form.record_date = String(route.query.date)
  loadDate()
})
</script>
