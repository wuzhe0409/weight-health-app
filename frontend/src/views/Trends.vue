<template>
  <div class="page">
    <h2>趋势</h2>

    <div class="section">
      <el-row :gutter="12">
        <el-col :span="6"><el-card shadow="never">最低体重<br /><b style="font-size:20px;color:#67c23a">{{ summary.min }}</b> kg</el-card></el-col>
        <el-col :span="6"><el-card shadow="never">最高体重<br /><b style="font-size:20px;color:#f56c6c">{{ summary.max }}</b> kg</el-card></el-col>
        <el-col :span="6"><el-card shadow="never">最近7日均重<br /><b style="font-size:20px;color:#7C3AED">{{ summary.recentAvg7 }}</b> kg</el-card></el-col>
        <el-col :span="6"><el-card shadow="never">经前−经后<br /><b style="font-size:20px">{{ summary.preMinusPost ?? '—' }}</b> kg</el-card></el-col>
      </el-row>
    </div>

    <div class="section">
      <el-card>
        <template #header>每日体重 与 7 日滚动平均（点色=排便：红未排/绿已排/橙前日未排）</template>
        <div ref="weightChart" style="height:340px"></div>
      </el-card>
    </div>

    <div class="section">
      <el-card>
        <template #header>每日热量区间（估算下限~上限，绿点为确认值）</template>
        <div ref="calChart" style="height:300px"></div>
      </el-card>
    </div>

    <div class="section">
      <el-card>
        <template #header>按食物关键词搜索</template>
        <el-input v-model="keyword" placeholder="如 西瓜、汉堡王、酸奶" style="max-width:320px" @keyup.enter="doSearch" />
        <el-button type="primary" @click="doSearch" style="margin-left:8px">搜索</el-button>
        <el-table v-if="results.length" :data="results" style="margin-top:12px" @row-click="(r:any)=>goDay(r.record_date)">
          <el-table-column prop="record_date" label="日期" width="120" />
          <el-table-column prop="meal_type" label="餐次" width="90" />
          <el-table-column prop="food_name" label="食物" />
          <el-table-column prop="kcal_source" label="来源" width="120" />
        </el-table>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import api from '@/api'

const router = useRouter()
const weightChart = ref<HTMLElement | null>(null)
const calChart = ref<HTMLElement | null>(null)
const keyword = ref('')
const results = ref<any[]>([])
const summary = ref<Record<string, any>>({})

let wChart: echarts.ECharts | null = null
let cChart: echarts.ECharts | null = null

const bowelColor: Record<string, string> = {
  no: '#f56c6c', yes: '#67c23a', previous_day_no: '#e6a23c',
  previous_day_yes: '#95d475', no_then_evening_yes: '#f56c6c',
  previous_evening_yes: '#95d475', unknown: '#c0c4cc',
}

function goDay(date: string) { router.push(`/day/${date}`) }

async function doSearch() {
  if (!keyword.value.trim()) return
  const { data } = await api.searchFood(keyword.value.trim())
  results.value = data
}

function periodBands(trend: any[]): any[] {
  // contiguous runs whose period_status includes 'period' -> markArea pairs
  const bands: any[] = []
  let start: string | null = null
  let color = 'rgba(230,162,60,0.10)'
  const flush = (end: string) => {
    if (start) bands.push([{ xAxis: start, itemStyle: { color } }, { xAxis: end }])
  }
  trend.forEach((p, i) => {
    const isP = !!p.period_status && p.period_status.includes('period')
    if (isP) {
      color = p.period_status!.includes('pre') ? 'rgba(230,162,60,0.12)'
        : p.period_status!.startsWith('period_day') ? 'rgba(245,108,108,0.12)'
        : 'rgba(103,194,58,0.12)'
      if (!start) start = p.record_date
    } else if (start) {
      flush(p.record_date)
      start = null
    }
    if (i === trend.length - 1 && start) flush(p.record_date)
  })
  return bands
}

async function render() {
  const [{ data: trend }, { data: cal }, { data: cycle }] = await Promise.all([
    api.weightTrend(), api.calories(), api.cycle(),
  ])
  const dates = trend.map((t: any) => t.record_date)
  const weights = trend.map((t: any) => ({
    value: t.weight_kg,
    itemStyle: { color: bowelColor[t.bowel_movement] || '#7C3AED' },
    avg7: t.avg7, bowel: t.bowel_movement, period: t.period_status,
  }))
  const avg7 = trend.map((t: any) => t.avg7)

  const bands = periodBands(trend)
  const bandArea = bands.length ? { silent: true, data: bands } : undefined

  wChart = echarts.init(weightChart.value!)
  wChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['体重', '7日均重'] },
    grid: { left: 40, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', scale: true, name: 'kg' },
    series: [
      {
        name: '体重', type: 'line', data: weights, smooth: true, symbolSize: 7,
        lineStyle: { color: '#7C3AED', width: 3 },
        itemStyle: { color: '#7C3AED' },
        markArea: bandArea,
        markPoint: { data: [{ type: 'min', name: '最低' }, { type: 'max', name: '最高' }] },
      },
      { name: '7日均重', type: 'line', data: avg7, smooth: true, lineStyle: { type: 'dashed', color: '#A855F7', width: 2 }, symbol: 'none' },
    ],
  })

  // calories range band
  const mins = cal.map((c: any) => c.total_kcal_min)
  const maxMinus = cal.map((c: any) => (c.total_kcal_max != null && c.total_kcal_min != null) ? c.total_kcal_max - c.total_kcal_min : null)
  const maxs = cal.map((c: any) => c.total_kcal_max)
  const confirmed = cal.map((c: any) => c.total_kcal_confirmed)
  const calDates = cal.map((c: any) => c.record_date)

  cChart = echarts.init(calChart.value!)
  cChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['热量下限', '区间', '热量上限', '确认值'] },
    grid: { left: 50, right: 20, top: 40, bottom: 30 },
    xAxis: { type: 'category', data: calDates },
    yAxis: { type: 'value', name: 'kcal' },
    series: [
      { name: '热量下限', type: 'line', stack: 'cal', data: mins, lineStyle: { opacity: 0 }, symbol: 'none', areaStyle: { opacity: 0 } },
      { name: '区间', type: 'line', stack: 'cal', data: maxMinus, lineStyle: { opacity: 0 }, symbol: 'none', areaStyle: { color: 'rgba(124,58,237,0.18)' } },
      { name: '热量上限', type: 'line', data: maxs, lineStyle: { color: '#7C3AED', width: 2 }, symbol: 'none' },
      { name: '确认值', type: 'scatter', data: confirmed.map((v: any, i: number) => (v != null ? [calDates[i], v] : null)).filter(Boolean), symbolSize: 9, itemStyle: { color: '#7C3AED' } },
    ],
  })

  const ws = trend.map((t: any) => t.weight_kg).filter((v: any) => v != null)
  summary.value = ws.length
    ? {
        min: Math.min(...ws).toFixed(2),
        max: Math.max(...ws).toFixed(2),
        recentAvg7: (avg7[avg7.length - 1] ?? '—'),
        preMinusPost: cycle.pre_minus_post_delta ?? '—',
      }
    : { min: '—', max: '—', recentAvg7: '—', preMinusPost: '—' }
}

function onResize() { wChart?.resize(); cChart?.resize() }

onMounted(() => { render(); window.addEventListener('resize', onResize) })
onBeforeUnmount(() => { window.removeEventListener('resize', onResize); wChart?.dispose(); cChart?.dispose() })
</script>
