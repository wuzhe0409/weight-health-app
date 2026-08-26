<template>
  <div class="page">
    <h2>AI 营养顾问</h2>

    <!-- ============================================================
        Chat dialog
       ============================================================ -->
    <el-card class="section chat-card">
      <template #header>
        <span class="accent-title">💬 对话</span>
        <span class="muted" style="margin-left:8px;font-weight:400">
          输入饮食记录或提问 · 支持 Ctrl+V 粘贴图片 · Ctrl+Enter 发送
        </span>
        <el-button size="small" text style="float:right" @click="clearHistory">清空对话</el-button>
      </template>

      <!-- Quick actions -->
      <div class="quick-actions">
        <el-tag v-for="qa in quickActions" :key="qa" class="quick-tag" @click="useQuickAction(qa)">{{ qa }}</el-tag>
      </div>

      <div class="chat-messages" v-if="chatMessages.length" ref="chatBox">
        <div v-for="(m, i) in chatMessages" :key="i" :class="m.role === 'user' ? 'chat-msg-user' : 'chat-msg-ai'">
          <div class="chat-bubble" v-html="renderMd(m.content)" />
          <div v-if="m.images && m.images.length" class="chat-images">
            <img v-for="(img, j) in m.images" :key="j" :src="img.dataUrl" class="chat-thumb" />
          </div>
        </div>
        <div v-if="chatLoading" class="chat-msg-ai">
          <div class="chat-bubble"><el-icon class="is-loading"><Loading /></el-icon> AI 思考中…</div>
        </div>
      </div>

      <div class="paste-area" @paste="onPaste">
        <el-input v-model="nlText" type="textarea" :rows="3" placeholder="8月5日 体重49.0 早饭吃了... 午饭..." @keydown.enter.ctrl="onSendChat" />
        <div v-if="imageList.length" class="image-preview-row">
          <div v-for="(img, i) in imageList" :key="i" class="image-preview-item">
            <img :src="img.dataUrl" />
            <el-button size="small" circle @click="removeImage(i)" class="img-remove-btn">✕</el-button>
          </div>
        </div>
      </div>

      <div style="margin-top:10px;display:flex;gap:10px;align-items:center">
        <el-button type="primary" @click="onSendAI" :loading="anyLoading" :disabled="!canSend">
          <el-icon style="margin-right:4px"><Promotion /></el-icon>发 送
        </el-button>
        <span v-if="intentHint" class="intent-hint" :class="`intent-${intent}`">
          → {{ intentHint }}
        </span>
      </div>
    </el-card>

    <!-- ============================================================
        AI Analyze result + Save to record
       ============================================================ -->
    <div class="section" v-if="aiResult">
      <el-card>
        <template #header>
          <div style="display:flex;align-items:center;justify-content:space-between">
            <span class="accent-title">分析结果</span>
            <div>
              <el-tag v-if="aiResult.score != null" type="warning" effect="dark" style="margin-right:10px">评分 {{ aiResult.score }}</el-tag>
              <el-button type="success" @click="saveToRecord" :loading="saving">保存记录</el-button>
              <el-button size="small" style="margin-left:8px" @click="jumpToToday" :disabled="!savedDate">去今日记录查看 →</el-button>
            </div>
          </div>
        </template>

        <div v-if="aiResult.kcal_breakdown && aiResult.kcal_breakdown.length">
          <div class="accent-title" style="margin-bottom:8px">热量估算明细</div>
          <el-table :data="aiResult.kcal_breakdown" size="small" border>
            <el-table-column prop="meal" label="餐次" width="80" />
            <el-table-column prop="food" label="食物" />
            <el-table-column prop="quantity" label="份量" width="160" />
            <el-table-column label="热量" width="130">
              <template #default="{ row }">
                <span v-if="row.kcal_min != null && row.kcal_max != null">{{ row.kcal_min }}~{{ row.kcal_max }}</span>
                <span v-else class="muted">未估算</span>
              </template>
            </el-table-column>
            <el-table-column prop="note" label="说明" min-width="160" />
          </el-table>
          <div style="margin-top:10px;font-size:15px">
            今日总热量：<b class="stat-num-purple">{{ aiResult.structured?.total_kcal_min ?? '—' }} ~ {{ aiResult.structured?.total_kcal_max ?? '—' }}</b> kcal
          </div>
        </div>

        <div v-if="aiResult.weight_analysis" style="margin-top:16px">
          <div class="accent-title" style="margin-bottom:8px">体重分析</div>
          <div class="ai-markdown" v-html="renderMd(aiResult.weight_analysis)" />
        </div>
        <div v-if="aiResult.weight_prediction" style="margin-top:16px">
          <div class="accent-title" style="margin-bottom:8px">明天体重预测</div>
          <div class="ai-markdown" v-html="renderMd(aiResult.weight_prediction)" />
        </div>
        <div v-if="aiResult.suggestions" style="margin-top:16px">
          <div class="accent-title" style="margin-bottom:8px">建议</div>
          <div class="ai-markdown" v-html="renderMd(aiResult.suggestions)" />
        </div>

        <!-- Fallback: 模型未返回结构化分析（如图片不兼容 / 配置错误）时展示原始提示 -->
        <el-alert
          v-if="aiResult.markdown && !hasStructuredContent(aiResult)"
          type="warning" :closable="false"
          :title="extractTitle(aiResult.markdown)"
          style="margin-top:12px"
        >
          <div v-html="renderMd(aiResult.markdown)" style="white-space:pre-wrap;line-height:1.7" />
        </el-alert>
      </el-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { MagicStick, Loading, Promotion } from '@element-plus/icons-vue'
import api from '@/api'

const CHAT_STORAGE_KEY = 'weight-health-chat-history'

const router = useRouter()
const nlText = ref('')
const imageList = ref<{ name: string; dataUrl: string }[]>([])
const aiLoading = ref(false)
const chatLoading = ref(false)
const saving = ref(false)
const aiResult = ref<any>(null)
const savedDate = ref('')
const chatMessages = ref<{ role: string; content: string; images?: { name: string; dataUrl: string }[] }[]>([])
const chatBox = ref<HTMLElement | null>(null)

const quickActions = [
  '我今天还能吃什么？',
  '分析一下我这周的体重趋势',
  '最近饮食有什么问题吗？',
  '明天体重会涨还是跌？',
]

// ── Intent detection (single send button) ──
function detectIntent(text: string, hasImage: boolean): 'analyze' | 'chat' {
  const t = (text || '').trim()
  // Any uploaded image → must go through analyze (multimodal)
  if (hasImage) return 'analyze'
  // Multi-date weight entries → analyze (batch fill path)
  if (t && extractMultiDayData(t).length >= 1) return 'analyze'

  // Conversational follow-up WITHOUT record markers → chat, never analyze.
  // e.g. "菜团子应该有个300卡 我感觉鸡公煲可能有800-1000 你觉得呢" is the
  // user DISCUSSING a previous estimate, not logging a new record.
  const hasRecordMarkers = /[早午晚]餐|[早午晚]饭|吃了|喝了|加餐|零食|夜宵|排便|拉了|拉屎|大便|月经|生理期|大姨妈|例假|经期|kg|公斤|斤|日|号/.test(t)
  if (!hasRecordMarkers &&
      /(你觉得|你说|对吧|对吗|我觉得|我感觉|我认为|高估|低估|偏高|偏低|重估|重新估|调整|应该|大概|可能|差不多|呢)/.test(t)) {
    return 'chat'
  }

  // Standalone weight number → analyze
  if (/(\d{2,3}(?:\.\d+)?)\s*(?:kg|公斤|斤)/.test(t)) return 'analyze'
  // Food / meal / bowel / period keywords → analyze (will save a record)
  if (/[早午晚]餐|[早午晚]饭|吃了|喝了|加餐|零食|夜宵|排便|拉了|拉屎|大便|月经|生理期|大姨妈|例假|经期/.test(t)) return 'analyze'
  // Pure question → chat
  if (/[?？]/.test(t)) return 'chat'
  if (/(为什么|怎么|咋|哪|啥|什么|是不是|能否|会不会|怎样|如何|几|多少)/.test(t)) return 'chat'
  // Default: short question-like → chat, long descriptive → analyze
  if (t.length < 30 && !/\d/.test(t)) return 'chat'
  // With conversation history, ambiguous text is more likely a follow-up
  // than a fresh record — prefer chat (the model can still query tools).
  if (chatMessages.value.length > 0) return 'chat'
  return 'analyze'
}

const intent = computed<'analyze' | 'chat' | null>(() => {
  const t = nlText.value.trim()
  if (!t && !imageList.value.length) return null
  return detectIntent(t, imageList.value.length > 0)
})
const intentHint = computed(() => {
  if (intent.value === 'analyze') return '智能分析（将解析饮食/热量/多日体重）'
  if (intent.value === 'chat') return '提问聊天'
  return ''
})
const canSend = computed(() => nlText.value.trim().length > 0 || imageList.value.length > 0)
const anyLoading = computed(() => aiLoading.value || chatLoading.value)

function useQuickAction(qa: string) {
  nlText.value = qa
  // Quick actions are questions, default to chat intent — don't auto-send so
  // the user can edit. Just trigger the reactive hint update by leaving
  // the value change; intent will be picked up by the button label.
}

// ── Persistent history (V2) ──
function loadHistory() {
  try {
    const saved = localStorage.getItem(CHAT_STORAGE_KEY)
    if (saved) chatMessages.value = JSON.parse(saved)
  } catch { /* ignore */ }
}
function saveHistory() {
  try {
    // Only save last 30 messages to avoid bloating
    const recent = chatMessages.value.slice(-30)
    localStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(recent))
  } catch { /* ignore */ }
}
function clearHistory() {
  chatMessages.value = []
  localStorage.removeItem(CHAT_STORAGE_KEY)
  ElMessage.success('对话已清空')
}
watch(chatMessages, () => saveHistory(), { deep: true })
onMounted(loadHistory)

function renderMd(text: string) {
  if (!text) return ''
  return text
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function hasStructuredContent(r: any) {
  return !!(r?.kcal_breakdown?.length || r?.weight_analysis || r?.suggestions)
}

function extractTitle(md: string) {
  // 把 markdown 里第一个 **...** 当作 alert 标题
  const m = (md || '').match(/\*\*(.+?)\*\*/)
  return m ? m[1].replace(/\n/g, ' ') : 'AI 反馈'
}

function onPaste(e: ClipboardEvent) {
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of Array.from(items)) {
    if (!item.type.startsWith('image/')) continue
    e.preventDefault()
    const file = item.getAsFile()
    if (!file) continue
    const reader = new FileReader()
    reader.onload = () => imageList.value.push({ name: `clipboard-${Date.now()}.png`, dataUrl: String(reader.result) })
    reader.readAsDataURL(file)
  }
}
function removeImage(i: number) { imageList.value.splice(i, 1) }

function scrollChat() {
  nextTick(() => { if (chatBox.value) chatBox.value.scrollTop = chatBox.value.scrollHeight })
}

// ---- AI Chat ----
// Compact digest of the last analysis so the chat model can DISCUSS its own
// previous estimates (without it, follow-ups like "鸡公煲应该有800-1000吧"
// hit a model that has no idea what it estimated before).
function analysisDigest(): string {
  const r = aiResult.value
  if (!r || !Array.isArray(r.kcal_breakdown) || !r.kcal_breakdown.length) return ''
  const items = r.kcal_breakdown
    .map((b: any) => `${b.food}(${b.kcal_min ?? '?'}~${b.kcal_max ?? '?'})`)
    .join('、')
  const total = `总计${r.structured?.total_kcal_min ?? '?'}~${r.structured?.total_kcal_max ?? '?'}kcal`
  return `上一轮AI热量估算：${items}，${total}`
}

async function onSendChat() {
  const msg = nlText.value.trim()
  if (!msg) return
  const imgs = imageList.value.length ? [...imageList.value] : []
  chatMessages.value.push({ role: 'user', content: msg, images: imgs })
  nlText.value = ''
  imageList.value = []
  chatLoading.value = true
  await nextTick(); scrollChat()

  try {
    const history = chatMessages.value.slice(0, -1).map(m => ({ role: m.role, content: m.content }))
    // Attach the previous estimate as context (sent to the model only,
    // the visible bubble stays clean).
    const digest = analysisDigest()
    const outgoing = digest ? `${msg}\n\n（上下文参考：${digest}）` : msg
    const { data } = await api.aiChat(outgoing, history)
    chatMessages.value.push({ role: 'assistant', content: data.reply })
  } catch (e: any) {
    chatMessages.value.push({ role: 'assistant', content: `出错了：${e.response?.data?.detail || e.message}` })
  } finally {
    chatLoading.value = false
    await nextTick(); scrollChat()
  }
}

// ── V2: Multi-date extraction & batch fill ──
interface MultiDayItem {
  record_date: string
  weight_kg: number | null
  bowel_movement: string
  period_status: string | null
  period_day: number | null
  period_days_until: number | null
}

// Detect period status from a text segment.
// Returns [period_status, period_day, period_days_until] — same shape as nlp_parser.
function extractPeriod(text: string): [string | null, number | null, number | null] {
  let m
  // 第X天 / 第一/二/三/四天 / X天 (when X is small integer 1-9)
  if ((m = text.match(/月经第\s*(\d+)\s*天/))) return [`period_day_${m[1]}`, parseInt(m[1]), null]
  if ((m = text.match(/月经第一\s*天/))) return ['period_day_1', 1, null]
  if ((m = text.match(/月经第二\s*天/))) return ['period_day_2', 2, null]
  if ((m = text.match(/月经第三\s*天/))) return ['period_day_3', 3, null]
  if ((m = text.match(/月经第四\s*天/))) return ['period_day_4', 4, null]
  if ((m = text.match(/月经第五\s*天/))) return ['period_day_5', 5, null]
  if ((m = text.match(/还有\s*(\d+)\s*天.*?(?:来|例假|月经|大姨妈)/))) return [`pre_period_${m[1]}_days`, null, parseInt(m[1])]
  if (/来例假|月经来了|生理期到了|大姨妈来了|来大姨妈|例假来了|经期来了/.test(text)) return ['period', null, null]
  if (/结束后|生理期结束|例假结束|月经结束|经期结束/.test(text)) return ['period_ended', null, null]
  return [null, null, null]
}

function extractMultiDayData(text: string): MultiDayItem[] {
  const now = new Date()
  const year = now.getFullYear()
  const currentMonth = now.getMonth() + 1
  // Two passes:
  //  1. Full dates: 8.8号 / 8月8日 / 8/8 / 8.8
  //  2. Single day: 10号 / 5日 → current month + day
  // Then sort by position in the original text.
  const matches: { index: number; month: number; day: number; end: number }[] = []
  let m: RegExpExecArray | null

  // Pass 1: full dates with month+day separator
  const fullPattern = /(\d{1,2})[\.月\/]\s*(\d{1,2})\s*([日号]?)/g
  while ((m = fullPattern.exec(text)) !== null) {
    const month = parseInt(m[1])
    const day = parseInt(m[2])
    const hasMarker = !!m[3]
    // Accept only if explicitly marked (日/号) OR both numbers in valid range.
    if (hasMarker || (month >= 1 && month <= 12 && day >= 1 && day <= 31)) {
      matches.push({ index: m.index, month, day, end: m.index + m[0].length })
    }
  }

  // Pass 2: short form like "10号" / "5日" → current month
  const shortPattern = /(?<![\d.月/])(\d{1,2})\s*([日号])(?![\d])/g
  while ((m = shortPattern.exec(text)) !== null) {
    const day = parseInt(m[1])
    if (day < 1 || day > 31) continue
    const idx = m.index
    // Skip if this is part of a full date already captured by pass 1
    const overlap = matches.some(x => idx >= x.index && idx < x.end)
    if (!overlap) {
      matches.push({ index: idx, month: currentMonth, day, end: idx + m[0].length })
    }
  }

  if (matches.length === 0) return []
  // Sort by original text position (so segments are in order)
  matches.sort((a, b) => a.index - b.index)

  // Global bowel detection (for patterns like "10号和11号都没有拉粑粑")
  let globalBowel = 'unknown'
  // Match both 没拉 and 没有拉 (没+有+拉 where 没 is separated by 有 from 拉)
  if (/(?:没(?:拉|排便|上)|未(?:拉|排便)|没有(?:拉|排便|上))/.test(text)) globalBowel = 'no'
  else if (/(?:拉(?:了|粑粑|屎)|排便|上了|上厕所)/.test(text)) globalBowel = 'yes'

  // Global period detection (for patterns like "10号和11号都来例假")
  const [gStatus, gDay, gUntil] = extractPeriod(text)
  const hasGlobalPeriod = !!gStatus

  const results: MultiDayItem[] = []
  for (let i = 0; i < matches.length; i++) {
    const { month, day, end } = matches[i]
    const recordDate = `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
    // Segment between this date and the next (or end of text)
    const nextStart = i + 1 < matches.length ? matches[i + 1].index : text.length
    const segment = text.slice(end, nextStart)

    // First number in the segment (2-3 digits, optional decimal) — weight
    const weightMatch = segment.match(/(\d{2,3}(?:[\.\,]\d+)?)/)
    const weight = weightMatch ? parseFloat(weightMatch[1].replace(',', '.')) : null

    // Per-segment bowel takes precedence; fall back to global detection
    let bowel = 'unknown'
    if (/(?:没(?:拉|排便|上)|未(?:拉|排便)|没有(?:拉|排便|上))/.test(segment)) bowel = 'no'
    else if (/(?:拉(?:了|粑粑|屎)|排便|上了|上厕所)/.test(segment)) bowel = 'yes'
    if (bowel === 'unknown') bowel = globalBowel

    // Per-segment period takes precedence; fall back to global detection
    const [sStatus, sDay, sUntil] = extractPeriod(segment)
    const period_status = sStatus || (hasGlobalPeriod ? gStatus : null)
    const period_day = sDay != null ? sDay : (hasGlobalPeriod ? gDay : null)
    const period_days_until = sUntil != null ? sUntil : (hasGlobalPeriod ? gUntil : null)

    results.push({
      record_date: recordDate,
      weight_kg: weight,
      bowel_movement: bowel,
      period_status,
      period_day,
      period_days_until,
    })
  }
  return results
}

async function checkExistingDates(dates: string[]): Promise<Map<string, boolean>> {
  // Single batch request instead of N serial GET /records/{date} calls.
  const result = new Map<string, boolean>(dates.map(d => [d, false]))
  try {
    const { data } = await api.batchExists(dates)
    for (const d of data.existing || []) result.set(d, true)
  } catch { /* fall back to all-new on error */ }
  return result
}

async function doBatchFill(items: MultiDayItem[], existingMap: Map<string, boolean>) {
  // Build confirm message lines
  const periodLabel = (item: MultiDayItem) => {
    if (!item.period_status) return ''
    if (item.period_status === 'period') return '经期开始'
    if (item.period_status === 'period_ended') return '经期结束'
    if (item.period_day != null) return `经期第${item.period_day}天`
    if (item.period_days_until != null) return `距经期${item.period_days_until}天`
    return ''
  }
  const lines = items.map(item => {
    const exists = existingMap.get(item.record_date)
    const prefix = exists ? '⚠️' : '✅'
    const status = exists ? '已有记录 → 将覆盖' : '新建记录'
    // Show only fields that are being updated (avoid noise)
    const parts: string[] = []
    if (item.weight_kg != null) parts.push(`体重 ${item.weight_kg}kg`)
    if (item.bowel_movement === 'yes') parts.push('已排便')
    else if (item.bowel_movement === 'no') parts.push('未排便')
    const p = periodLabel(item)
    if (p) parts.push(p)
    return `${prefix} ${item.record_date}（${status}）：${parts.join('，') || '（无内容）'}`
  }).join('\n')

  await ElMessageBox.confirm(lines, '确认批量回填数据', {
    confirmButtonText: '确认回填',
    cancelButtonText: '取消',
    type: 'warning',
    distinguishCancelAndClose: true,
    closeOnClickModal: false,
  })

  const { data } = await api.batchFill(items)
  const created = data.total_created || 0
  const updated = data.total_updated || 0
  const skipped = data.total_skipped || 0

  const parts: string[] = []
  if (created > 0) parts.push(`新建 ${created} 条`)
  if (updated > 0) parts.push(`更新 ${updated} 条`)
  if (skipped > 0) parts.push(`跳过 ${skipped} 条（已锁定）`)
  ElMessage.success(parts.join('，'))
}

// ---- AI Analyze ----
async function onAiAnalyze() {
  if (!nlText.value.trim() && !imageList.value.length) { ElMessage.warning('请先输入文字或粘贴图片'); return }

  const text = nlText.value.trim()
  // Mirror user message into chat history so it shows alongside chat replies
  const imgs = imageList.value.length ? [...imageList.value] : []
  chatMessages.value.push({ role: 'user', content: text, images: imgs })
  await nextTick(); scrollChat()

  // ── V2: Multi-date backfill path ──
  const multiDayItems = extractMultiDayData(text)
  if (multiDayItems.length >= 1) {
    const existingMap = await checkExistingDates(multiDayItems.map(i => i.record_date))
    const hasExisting = multiDayItems.some(i => existingMap.get(i.record_date))

    if (hasExisting) {
      // Some dates have existing records → show confirm dialog
      try {
        await doBatchFill(multiDayItems, existingMap)
      } catch {
        // User cancelled: drop the placeholder user message we pushed earlier
        chatMessages.value.pop()
        return
      }
    } else {
      // All new dates → fill directly
      const { data } = await api.batchFill(multiDayItems)
      ElMessage.success(`已回填 ${data.total_created || multiDayItems.length} 天体重数据`)
      chatMessages.value.push({ role: 'assistant', content: `✅ 体重已回填 ${data.total_created || multiDayItems.length} 天` })
    }

    // After batch fill, check if there's food content worth analyzing
    const hasMealContent = /[早午晚]餐|[早午晚饭]|吃了|喝了|加餐|零食|夜宵|麻辣|炒|煮|烤|蒸|拌|米饭|面|饼|包子|饺子/.test(text)
    if (!hasMealContent && !imageList.value.length) {
      nlText.value = ''
      imageList.value = []
      chatMessages.value.push({ role: 'assistant', content: `✅ 体重已回填${multiDayItems.length > 1 ? `（${multiDayItems.length} 天）` : ''}` })
      await nextTick(); scrollChat()
      return // pure weight entry, no AI analysis needed
    }

    // Has food content → also do AI analysis for the latest date
    aiLoading.value = true
    try {
      const latestDate = multiDayItems[multiDayItems.length - 1].record_date
      const { data } = await api.aiAnalyze({
        text,
        record_date: latestDate,
        images: imageList.value.map(i => i.dataUrl),
      })
      aiResult.value = data
      savedDate.value = data.structured?.record_date || latestDate
      ElMessage.success('饮食分析完成，点击「保存记录」可补充饮食数据')
      const summary = [data.weight_analysis, data.weight_prediction, data.suggestions].filter(Boolean).join('\n\n')
      if (summary) chatMessages.value.push({ role: 'assistant', content: summary })
    } catch (e: any) {
      chatMessages.value.push({ role: 'assistant', content: `分析失败：${e.response?.data?.detail || e.message}` })
      ElMessage.warning('饮食分析失败，但体重数据已回填')
    } finally { aiLoading.value = false }
    nlText.value = ''
    imageList.value = []
    await nextTick(); scrollChat()
    return
  }

  // ── Normal single-date AI analysis (unchanged) ──
  aiLoading.value = true
  try {
    const { data } = await api.aiAnalyze({
      text: nlText.value,
      record_date: new Date().toISOString().slice(0, 10),
      images: imageList.value.map(i => i.dataUrl),
    })
    aiResult.value = data
    savedDate.value = data.structured?.record_date || ''
    if (data.kcal_breakdown?.length || data.weight_analysis || data.suggestions) {
      ElMessage.success('分析完成，点击「保存记录」即可存入')
    } else if (data.image_note) {
      ElMessage.warning('当前模型不支持图片，已跳过图片分析')
    } else if (data.markdown) {
      ElMessage.warning(data.markdown.slice(0, 60))
    } else {
      ElMessage.warning('AI 未返回结构化结果')
    }
    // Push summary into chat history
    const summary = [data.weight_analysis, data.weight_prediction, data.suggestions].filter(Boolean).join('\n\n')
    if (summary) chatMessages.value.push({ role: 'assistant', content: summary })
  } catch (e: any) {
    chatMessages.value.push({ role: 'assistant', content: `出错了：${e.response?.data?.detail || e.message}` })
    ElMessage.error(`分析失败：${e.response?.data?.detail || e.message}`)
  } finally { aiLoading.value = false }
  // Clear input + images after analyze
  nlText.value = ''
  imageList.value = []
  await nextTick(); scrollChat()
}

// ---- Unified send (auto-routes to analyze or chat) ----
async function onSendAI() {
  if (!canSend.value || anyLoading.value) return
  if (intent.value === 'analyze') return onAiAnalyze()
  return onSendChat()
}

// ---- Save to record ----
async function saveToRecord() {
  if (!aiResult.value) return
  const s = aiResult.value.structured || {}
  const recordDate = s.record_date || new Date().toISOString().slice(0, 10)

  const foodEntries = (aiResult.value.kcal_breakdown || []).map((item: any) => ({
    meal_type: item.meal || 'snack',
    food_name: item.food || '',
    quantity_text: item.quantity || '',
    kcal: item.kcal_max ?? item.kcal_min ?? null,
    kcal_source: 'estimated',
  }))

  const payload = {
    record_date: recordDate,
    weight_kg: s.weight_kg ?? null,
    bowel_movement: s.bowel_movement || 'unknown',
    period_status: s.period_status || null,
    period_day: s.period_day ?? null,
    period_days_until: s.period_days_until ?? null,
    total_kcal_min: s.total_kcal_min ?? null,
    total_kcal_max: s.total_kcal_max ?? null,
    total_kcal_confirmed: null,
    analysis: [aiResult.value.weight_analysis, aiResult.value.suggestions].filter(Boolean).join('\n\n'),
    notes: '',
    data_status: s.data_status || 'estimated',
    raw_input: null,
    food_entries: foodEntries,
  }

  saving.value = true
  try {
    // Check if already exists to decide save vs revision
    try {
      await api.getRecord(recordDate)
      // exists – use revision
      await api.revision(recordDate, payload)
      ElMessage.success('已更新保存（原记录已修订）')
    } catch {
      await api.saveRecord(payload)
      ElMessage.success(`已保存到 ${recordDate} 的记录`)
    }
    savedDate.value = recordDate
  } catch (e: any) {
    ElMessage.error(`保存失败：${e.response?.data?.detail || e.message}`)
  } finally { saving.value = false }
}

function jumpToToday() {
  if (savedDate.value) router.push(`/today?date=${savedDate.value}`)
}
</script>

<style scoped>
.chat-card { border: 2px solid var(--brand-200) !important; }
.chat-messages {
  max-height: 400px;
  overflow-y: auto;
  margin-bottom: 12px;
  padding-right: 4px;
}
.chat-msg-user { display: flex; justify-content: flex-end; margin-bottom: 10px; }
.chat-msg-ai   { display: flex; justify-content: flex-start; margin-bottom: 10px; }
.chat-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 14px;
  line-height: 1.65;
  font-size: 14px;
}
.chat-msg-user .chat-bubble {
  background: var(--brand-grad);
  color: #fff;
  border-bottom-right-radius: 4px;
}
.chat-msg-ai .chat-bubble {
  background: #f3f0fb;
  color: #2e293b;
  border-bottom-left-radius: 4px;
}
.chat-images { display: flex; gap: 6px; margin-top: 6px; flex-wrap: wrap; }
.chat-thumb { width: 80px; height: 80px; object-fit: cover; border-radius: 10px; border: 1px solid var(--brand-100); }

.paste-area {
  border: 2px dashed var(--brand-200);
  border-radius: 12px;
  padding: 10px;
  transition: border-color 0.2s;
}
.paste-area:focus-within { border-color: var(--brand-400); }

.image-preview-row { display: flex; gap: 8px; margin-top: 10px; flex-wrap: wrap; }
.image-preview-item { position: relative; width: 72px; height: 72px; }
.image-preview-item img { width: 100%; height: 100%; object-fit: cover; border-radius: 10px; border: 1px solid var(--brand-100); }
.img-remove-btn {
  position: absolute; top: -6px; right: -6px;
  width: 20px; height: 20px; font-size: 11px;
}

.ai-markdown {
  line-height: 1.7; color: #4b5563;
  background: #faf8ff; padding: 12px 14px;
  border-radius: 10px; border: 1px solid #ede7fb;
}

/* ── V2: 快速提问 ── */
.quick-actions {
  display: flex; gap: 8px; flex-wrap: wrap;
  margin-bottom: 12px; padding-bottom: 12px;
  border-bottom: 1px solid var(--brand-100);
}
.quick-tag {
  cursor: pointer; transition: all 0.2s;
  background: var(--brand-50); color: var(--brand-700);
  border-color: var(--brand-200);
}
.quick-tag:hover {
  background: var(--brand-200); color: var(--brand-900);
  transform: translateY(-1px);
}

/* ── Intent hint next to send button ── */
.intent-hint {
  font-size: 13px;
  color: var(--brand-700);
  font-weight: 500;
  letter-spacing: 0.3px;
}
.intent-hint.intent-chat { color: #909399; }
</style>
