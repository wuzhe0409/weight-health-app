<template>
  <div class="page" v-if="rec">
    <div style="display:flex;align-items:center;gap:12px">
      <h2 style="margin:0">{{ rec.record_date }}</h2>
      <el-tag v-if="rec.is_locked === 1" type="info">已锁定</el-tag>
      <el-tag :type="statusType(rec.data_status)">{{ statusLabel(rec.data_status) }}</el-tag>
      <el-button style="margin-left:auto" @click="edit">编辑（修订）</el-button>
    </div>

    <el-card class="section">
      <el-descriptions :column="3" border>
        <el-descriptions-item label="晨起体重">{{ rec.weight_kg ?? '—' }} kg</el-descriptions-item>
        <el-descriptions-item label="排便">{{ bowelLabel(rec.bowel_movement) }}</el-descriptions-item>
        <el-descriptions-item label="生理期">
          {{ rec.period_status || '—' }}
          <span v-if="rec.period_day">（第{{ rec.period_day }}天）</span>
          <span v-if="rec.period_days_until">（还有{{ rec.period_days_until }}天）</span>
        </el-descriptions-item>
        <el-descriptions-item label="热量区间">
          <template v-if="rec.total_kcal_min != null && rec.total_kcal_max != null">
            {{ rec.total_kcal_min }} ~ {{ rec.total_kcal_max }} kcal
          </template>
          <template v-else>—</template>
          <span v-if="rec.total_kcal_confirmed != null">（确认 {{ rec.total_kcal_confirmed }}）</span>
        </el-descriptions-item>
        <el-descriptions-item label="来源">{{ rec.source }}</el-descriptions-item>
        <el-descriptions-item label="备注">{{ rec.notes || '—' }}</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-card class="section">
      <template #header>饮食明细</template>
      <div v-for="meal in ['breakfast','lunch','dinner','snack','drink']" :key="meal" style="margin-bottom:14px">
        <div class="muted" style="margin-bottom:6px">{{ mealLabels[meal] }}（{{ foodsByMeal(meal).length }}）</div>
        <el-table v-if="foodsByMeal(meal).length" :data="foodsByMeal(meal)" size="small">
          <el-table-column prop="food_name" label="食物" />
          <el-table-column prop="quantity_text" label="数量" />
          <el-table-column label="热量" width="160">
            <template #default="{ row }">
              <span v-if="row.kcal != null">{{ row.kcal }} kcal</span>
              <span v-else-if="row.kcal_min != null || row.kcal_max != null">{{ row.kcal_min ?? '?' }}~{{ row.kcal_max ?? '?' }}</span>
              <span v-else>—</span>
            </template>
          </el-table-column>
          <el-table-column prop="kcal_source" label="来源" width="120" />
        </el-table>
      </div>
    </el-card>

    <el-card class="section">
      <template #header>分析与建议</template>
      <p>{{ rec.analysis || '—' }}</p>
    </el-card>

    <el-card class="section">
      <template #header>原始自然语言输入</template>
      <el-collapse>
        <el-collapse-item title="展开查看 raw_input">
          <pre style="white-space:pre-wrap">{{ rec.raw_input || '—' }}</pre>
        </el-collapse-item>
      </el-collapse>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import type { DailyRecord } from '@/types'

const route = useRoute()
const router = useRouter()
const rec = ref<DailyRecord | null>(null)

const mealLabels: Record<string, string> = {
  breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '加餐', drink: '饮料',
}
const bowelMap: Record<string, string> = {
  yes: '已排便', no: '未排便', previous_day_yes: '前一天排便', previous_day_no: '前一天未排便',
  no_then_evening_yes: '当晚才排便', previous_evening_yes: '前一晚排便', unknown: '未知',
}
function bowelLabel(b: string) { return bowelMap[b] || b }
function statusLabel(s: string) {
  return { confirmed: '已确认', mostly_confirmed: '基本确认', partially_confirmed: '部分确认', estimated: '估算', incomplete: '不完整' }[s] || s
}
function statusType(s: string) {
  return { confirmed: 'success', mostly_confirmed: 'success', partially_confirmed: 'warning', estimated: 'info', incomplete: 'danger' }[s] || 'info'
}
function foodsByMeal(meal: string) {
  return (rec.value?.food_entries || []).filter((f) => f.meal_type === meal)
}
function edit() { router.push({ path: '/today', query: { date: route.params.date } }) }

async function load() {
  const { data } = await api.getRecord(String(route.params.date))
  rec.value = data
}
onMounted(load)
watch(() => route.params.date, load)
</script>
