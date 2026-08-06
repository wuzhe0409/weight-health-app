<template>
  <div class="page">
    <h2>历史日历</h2>

    <div class="section">
      <el-card>
        <el-calendar v-model="picked">
          <template #date-cell="{ data }">
            <div @click="goDay(data.day)" style="height:100%;cursor:pointer">
              <div class="muted">{{ data.day.split('-')[2] }}</div>
              <div v-if="byDate[data.day]">
                <div style="font-weight:600;color:#409eff">{{ byDate[data.day].weight_kg ?? '' }}</div>
                <div style="font-size:11px;line-height:1.3">
                  <span v-if="byDate[data.day].bowel_movement === 'yes'" style="color:#67c23a">便</span>
                  <span v-else-if="byDate[data.day].bowel_movement === 'no'" style="color:#f56c6c">未</span>
                  <span v-if="isPeriod(byDate[data.day].period_status)" style="color:#e6a23c">经</span>
                  <span v-if="byDate[data.day].is_locked === 1" style="color:#909399">🔒</span>
                </div>
              </div>
            </div>
          </template>
        </el-calendar>
      </el-card>
    </div>

    <div class="section">
      <el-card>
        <template #header>搜索</template>
        <el-input v-model="keyword" placeholder="食物名称 / 品牌，如 西瓜、汉堡王" style="max-width:320px" @keyup.enter="doSearch" />
        <el-button type="primary" @click="doSearch" style="margin-left:8px">搜索</el-button>
        <el-table v-if="results.length" :data="results" style="margin-top:12px" @row-click="(r:any)=>goDay(r.record_date)">
          <el-table-column prop="record_date" label="日期" width="120" />
          <el-table-column prop="meal_type" label="餐次" width="90" />
          <el-table-column prop="food_name" label="食物" />
          <el-table-column prop="kcal_source" label="来源" width="120" />
        </el-table>
        <div v-else-if="searched" class="muted" style="margin-top:12px">未找到匹配项。</div>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import type { DailyRecord } from '@/types'

const router = useRouter()
const picked = ref(new Date())
const records = ref<DailyRecord[]>([])
const byDate = ref<Record<string, DailyRecord>>({})
const keyword = ref('')
const results = ref<any[]>([])
const searched = ref(false)

function isPeriod(s: string | null) {
  return !!s && (s.includes('period') || s === 'period')
}
function goDay(date: string) {
  router.push(`/day/${date}`)
}
async function load() {
  const { data } = await api.getRecords()
  records.value = data
  byDate.value = {}
  for (const r of data) byDate.value[r.record_date] = r
}
async function doSearch() {
  if (!keyword.value.trim()) return
  const { data } = await api.searchFood(keyword.value.trim())
  results.value = data
  searched.value = true
}
onMounted(load)
</script>
